# backend/app.py
#
# This is the main entry point for the backend server.
# It runs a Flask web server on http://127.0.0.1:5000
#
# The browser extension sends article text to this server via HTTP POST.
# This file receives it, runs the full analysis pipeline, and sends
# back a JSON response with the consistency score, related articles,
# tone indicators, and framing flags.
#
# Pipeline order:
#   1. Analyze tone of the user's article (TextBlob)
#   2. Analyze framing/language patterns (spaCy + regex)
#   3. Fetch related articles (NewsAPI)
#   4. Embed all articles as vectors (sentence-transformers)
#   5. Compute consistency score and rank related articles (numpy)

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from api.news_controller import fetch_related_articles
from model.embed_text import embed_texts
from model.numpy_compute import compute_scores, bias_indicators, consistency_label
from model.framing_analysis import analyze_framing

import os
import re

# Load environment variables from the .env file in this folder.
# This is how we read NEWSAPI_KEY without hardcoding it in the source code.
load_dotenv()

app = Flask(__name__)
CORS(app)  # allows the browser extension to talk to this server

# Read the NewsAPI key from the .env file
NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")
PORT = int(os.environ.get("PORT", 5000) or 5000)

MIN_TEXT_WORDS = 30
MAX_TEXT_CHARS = 50000
MAX_TITLE_CHARS = 300
MAX_URL_CHARS = 2048


def error_response(status: int, code: str, message: str, details: dict | None = None):
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status


def validate_analyze_payload(data):
    
    # Check that the request body is not empty
    if data is None:
        return None, error_response(
            400,
            "INVALID_JSON",
            "Expected a JSON request body.",
        )
		
	# Check that the JSON body is an object
    if not isinstance(data, dict):
        return None, error_response(
            400,
            "INVALID_PAYLOAD",
            "JSON body must be an object.",
        )



	# Extract and validate the title, url, and text fields
    title_raw = data.get("title", "")
    url_raw = data.get("url", "")
    text_raw = data.get("text", "")

    if title_raw is None:
        title_raw = ""
    if url_raw is None:
        url_raw = ""

    if not isinstance(title_raw, str) or not isinstance(url_raw, str) or not isinstance(text_raw, str):
        return None, error_response(
            400,
            "INVALID_FIELD_TYPE",
            "Fields title, url, and text must be strings.",
        )



	# Trim whitespace and validate lengths
    title = title_raw.strip()
    url = url_raw.strip()
    text = text_raw.strip()

    if not text:
        return None, error_response(400, "MISSING_TEXT", "No text provided.")

    if len(text) > MAX_TEXT_CHARS:
        return None, error_response(
            400,
            "TEXT_TOO_LONG",
            "Article text is too long.",
            details={"maxChars": MAX_TEXT_CHARS, "receivedChars": len(text)},
        )

    word_count = len(text.split())
    if word_count < MIN_TEXT_WORDS:
        return None, error_response(
            400,
            "TEXT_TOO_SHORT",
            "Article text is too short for credible analysis.",
            details={"minWords": MIN_TEXT_WORDS, "receivedWords": word_count},
        )

    if len(title) > MAX_TITLE_CHARS:
        return None, error_response(
            400,
            "TITLE_TOO_LONG",
            "Title is too long.",
            details={"maxChars": MAX_TITLE_CHARS, "receivedChars": len(title)},
        )

    if len(url) > MAX_URL_CHARS:
        return None, error_response(
            400,
            "URL_TOO_LONG",
            "URL is too long.",
            details={"maxChars": MAX_URL_CHARS, "receivedChars": len(url)},
        )



	# Basic URL format check
    if url and not (url.startswith("http://") or url.startswith("https://")):
        return None, error_response(
            400,
            "INVALID_URL",
            "URL must start with http:// or https://",
        )


	# If we made it this far, the input is valid. Return the cleaned data.
    return {
        "title": title,
        "url": url,
        "text": text,
        "word_count": word_count,
    }, None


def build_search_queries(title: str, text: str) -> list[str]:
    queries = []

    if title:
        base = re.split(r"\s+[|\-]\s+", title)[0].strip()
        base = base.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
        clean = re.sub(r"[^A-Za-z0-9\s]", " ", base)
        clean = re.sub(r"\s+", " ", clean).strip()

        words = clean.split()
        if words:
            queries.append(" ".join(words[:10]))
        if len(words) >= 6:
            queries.append(" ".join(words[:6]))

    if text:
        queries.append(" ".join(text.split()[:12]))

    # remove duplicates while preserving order
    seen = set()
    out = []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


@app.post("/analyze")
def analyze():
    """
    Main endpoint. The extension POSTs JSON with:
        { "title": "...", "url": "...", "text": "..." }

    Returns JSON with the full analysis result.
    """
    data = request.get_json(silent=True) or {}

    payload = {
        "title": (data.get("title") or "").strip(),
        "url": (data.get("url") or "").strip(),
        "text": (data.get("text") or "").strip(),
    }

    validated, validation_error = validate_analyze_payload(payload)
    if validation_error:
        return validation_error

    title = validated["title"]
    url = validated["url"]
    text = validated["text"]
    word_count = validated["word_count"]

    if not NEWS_API_KEY:
        return error_response(
            503,
            "MISSING_CONFIG",
            "Server is not configured with NEWSAPI_KEY.",
        )

    # --- Step 1 Tone analysis ---
    # Scores how opinionated vs factual the writing is, and its emotional charge
    try:
        tone = bias_indicators(text)
    except Exception:
        app.logger.exception("Tone analysis failed")
        return error_response(
            500,
            "TONE_ANALYSIS_FAILED",
            "Failed to analyze article tone.",
        )

    # --- Step 2 Framing analysis ---
    # Detects language patterns like selective doubt, passive voice,
    # and precision asymmetry that can indicate one-sided framing
    try:
        framing = analyze_framing(text)
    except Exception:
        app.logger.exception("Framing analysis failed")
        return error_response(
            500,
            "FRAMING_ANALYSIS_FAILED",
            "Failed to analyze article framing.",
        )

    # --- Step 3 Fetch related articles ---
    # Use the article title as the search query (fall back to first 120 chars of text)
    # query = title if title else text[:120]
    related_articles = []
    try:
        for query in build_search_queries(title, text):
            related_articles = fetch_related_articles(query, NEWS_API_KEY, num=10)
            if related_articles:
                break
    except Exception:
        app.logger.exception("Related article fetch failed")
        return error_response(
            502,
            "RELATED_FETCH_FAILED",
            "Failed to fetch related reporting.",
        )

    if not related_articles:
        return error_response(
            502,
            "NO_RELATED_ARTICLES",
            "No related articles were found from upstream providers.",
        )

    # --- Step 4 Embed everything as vectors ---
    # Combine the user's article with all related articles into one list,
    # then encode them all at once (faster than encoding separately)
    related_texts = [
        a["title"] + " " + a["description"]
        for a in related_articles
    ]

    all_texts      = [text[:2000]] + related_texts  # cap user text for speed
    try:
        all_embeddings = embed_texts(all_texts)
    except Exception:
        app.logger.exception("Embedding stage failed")
        return error_response(
            503,
            "EMBEDDING_UNAVAILABLE",
            "Text embedding service is unavailable.",
        )

    user_embedding     = all_embeddings[0]   # first row = user's article
    related_embeddings = all_embeddings[1:]  # remaining rows = related articles

    # --- Step 5 Score consistency and rank related articles ---
    try:
        scores = compute_scores(user_embedding, related_embeddings, related_articles)
    except Exception:
        app.logger.exception("Scoring stage failed")
        return error_response(
            500,
            "SCORING_FAILED",
            "Failed to compute credibility scoring.",
        )

    # Send the full result back to the extension
    return jsonify({
        "ok":    True,
        "input": {
            "title":     title,
            "url":       url,
            "wordCount": word_count,
        },
        "score":   scores["consistency_score"],  # 0-100, how consistent with the cluster
        "label": scores["label"],                 # written explanation
        "tone":    tone,                          # subjectivity + polarity
        "framing": framing,                       # language pattern flags
        "related": scores["related"],             # ranked list of related articles
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
