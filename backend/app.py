# ============================================================
# FILE: backend/app.py
# PURPOSE:
#   Main Flask backend for the news analysis system.
#
# WHAT THIS FILE DOES:
#   1) Receives article data from the browser extension
#   2) Validates the incoming JSON payload
#   3) Runs tone analysis
#   4) Runs framing analysis
#   5) Fetches related articles from NewsAPI
#   6) Embeds text into vectors
#   7) Computes similarity / consistency score
#   8) Returns everything to the extension as JSON
#
# CTRL+F TAGS:
#   [ENTRY_POINT]
#   [INPUT_VALIDATION]
#   [QUERY_BUILDING]
#   [RELATED_ARTICLES_LIMIT]
#   [CONSISTENCY_SCORE_OUTPUT]
#   [PIPELINE_ORDER]
#   [ERROR_HANDLING]
# ============================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from api.news_controller import fetch_related_articles
from model.embed_text import embed_texts
from model.numpy_compute import compute_scores, bias_indicators, consistency_label
from model.framing_analysis import analyze_framing

import os
import re

# Load environment variables from .env so secrets are not hardcoded.
# Example: NEWSAPI_KEY=xxxxx
load_dotenv()

app = Flask(__name__)
CORS(app)  # allows browser extension requests to reach this backend

# ============================================================
# [CONFIG]
# Read server configuration from environment variables.
# ============================================================
NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")
PORT = int(os.environ.get("PORT", 5000) or 5000)

# ============================================================
# [INPUT_VALIDATION_LIMITS]
# These constants define what input sizes are allowed.
#
# CTRL+F:
#   [MIN_WORD_REQUIREMENT]
#   [MAX_TEXT_LIMIT]
#   [MAX_TITLE_LIMIT]
#   [MAX_URL_LIMIT]
# ============================================================
MIN_TEXT_WORDS = 30
MAX_TEXT_CHARS = 50000
MAX_TITLE_CHARS = 300
MAX_URL_CHARS = 2048


def error_response(status: int, code: str, message: str, details: dict | None = None):
    """
    [ERROR_HANDLING]
    Standard helper for returning consistent JSON error responses.

    Why this exists:
    - keeps all errors in the same structure
    - makes frontend popup easier to debug
    - lets the extension show clean messages to the user
    """
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
    """
    [INPUT_VALIDATION]
    Validates and cleans the request body sent from the extension.

    Expected input:
        {
            "title": "...",
            "url": "...",
            "text": "..."
        }

    What this function checks:
    - body exists
    - body is a JSON object
    - title/url/text are strings
    - text is not empty
    - text is long enough for analysis
    - text/title/url are not too long
    - URL format starts with http:// or https://

    Returns:
    - cleaned payload dict if valid
    - error response if invalid
    """

    # Ensure the request body exists.
    if data is None:
        return None, error_response(
            400,
            "INVALID_JSON",
            "Expected a JSON request body.",
        )

    # Ensure the JSON body is actually an object/dictionary.
    if not isinstance(data, dict):
        return None, error_response(
            400,
            "INVALID_PAYLOAD",
            "JSON body must be an object.",
        )

    # Extract raw values. Default to empty strings if missing.
    title_raw = data.get("title", "")
    url_raw = data.get("url", "")
    text_raw = data.get("text", "")

    # Convert None values into empty strings so .strip() will not fail.
    if title_raw is None:
        title_raw = ""
    if url_raw is None:
        url_raw = ""

    # Reject non-string field types.
    if not isinstance(title_raw, str) or not isinstance(url_raw, str) or not isinstance(text_raw, str):
        return None, error_response(
            400,
            "INVALID_FIELD_TYPE",
            "Fields title, url, and text must be strings.",
        )

    # Remove leading/trailing whitespace.
    title = title_raw.strip()
    url = url_raw.strip()
    text = text_raw.strip()

    # [MIN_WORD_REQUIREMENT]
    # Reject empty article text.
    if not text:
        return None, error_response(400, "MISSING_TEXT", "No text provided.")

    # [MAX_TEXT_LIMIT]
    # Prevent extremely large payloads from slowing down the backend.
    if len(text) > MAX_TEXT_CHARS:
        return None, error_response(
            400,
            "TEXT_TOO_LONG",
            "Article text is too long.",
            details={"maxChars": MAX_TEXT_CHARS, "receivedChars": len(text)},
        )

    # Count words for quality control and frontend display.
    word_count = len(text.split())

    # Require enough words so the analysis is meaningful.
    if word_count < MIN_TEXT_WORDS:
        return None, error_response(
            400,
            "TEXT_TOO_SHORT",
            "Article text is too short for credible analysis.",
            details={"minWords": MIN_TEXT_WORDS, "receivedWords": word_count},
        )

    # [MAX_TITLE_LIMIT]
    if len(title) > MAX_TITLE_CHARS:
        return None, error_response(
            400,
            "TITLE_TOO_LONG",
            "Title is too long.",
            details={"maxChars": MAX_TITLE_CHARS, "receivedChars": len(title)},
        )

    # [MAX_URL_LIMIT]
    if len(url) > MAX_URL_CHARS:
        return None, error_response(
            400,
            "URL_TOO_LONG",
            "URL is too long.",
            details={"maxChars": MAX_URL_CHARS, "receivedChars": len(url)},
        )

    # Basic URL format check.
    if url and not (url.startswith("http://") or url.startswith("https://")):
        return None, error_response(
            400,
            "INVALID_URL",
            "URL must start with http:// or https://",
        )

    # Cleaned payload returned to the main route.
    return {
        "title": title,
        "url": url,
        "text": text,
        "word_count": word_count,
    }, None


def build_search_queries(title: str, text: str) -> list[str]:
    """
    [QUERY_BUILDING]
    Builds multiple fallback search queries from the article title.

    Why this exists:
    Sometimes the full title is too specific or too noisy for NewsAPI.
    This function creates a few shortened versions so the backend can try:
      - first ~10 words
      - first ~6 words
      - first ~3 words

    That improves the odds of finding related reporting.

    CTRL+F:
      [SEARCH_QUERY_FALLBACK]
      [TITLE_CLEANING]
    """
    queries = []

    if title:
        # Remove site suffixes or extra segments like:
        # "Headline | Site Name" or "Headline - Outlet"
        base = re.split(r"\s+[|\-]\s+", title)[0].strip()

        # Remove punctuation so the query is simpler.
        base = re.sub(r"[^A-Za-z0-9\s]", " ", base)
        base = re.sub(r"\s+", " ", base).strip()

        words = base.split()

        # Try multiple progressively shorter versions.
        if words:
            queries.append(" ".join(words[:10]))
        if len(words) >= 6:
            queries.append(" ".join(words[:6]))
        if len(words) >= 3:
            queries.append(" ".join(words[:3]))

    # Remove duplicates while preserving order.
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
    [ENTRY_POINT]
    Main backend endpoint called by the extension.

    Input from extension:
        {
            "title": "...",
            "url": "...",
            "text": "..."
        }

    Output to extension:
        {
            "ok": True,
            "input": {...},
            "score": ...,
            "label": ...,
            "tone": ...,
            "framing": ...,
            "related": [...]
        }

    [PIPELINE_ORDER]
    Backend pipeline:
      1. validate input
      2. tone analysis
      3. framing analysis
      4. fetch related articles
      5. embed text
      6. compute score
      7. return JSON
    """
    payload = request.get_json(silent=True)

    validated, validation_error = validate_analyze_payload(payload)
    if validation_error:
        return validation_error

    title = validated["title"]
    url = validated["url"]
    text = validated["text"]
    word_count = validated["word_count"]

    # Server cannot function without the NewsAPI key.
    if not NEWS_API_KEY:
        return error_response(
            503,
            "MISSING_CONFIG",
            "Server is not configured with NEWSAPI_KEY.",
        )

    # ========================================================
    # STEP 1: Tone analysis
    # [TONE_ANALYSIS]
    # Measures:
    #   - subjectivity
    #   - polarity
    # ========================================================
    try:
        tone = bias_indicators(text)
    except Exception:
        app.logger.exception("Tone analysis failed")
        return error_response(
            500,
            "TONE_ANALYSIS_FAILED",
            "Failed to analyze article tone.",
        )

    # ========================================================
    # STEP 2: Framing analysis
    # [FRAMING_ANALYSIS]
    # Detects:
    #   - hedging / doubt language
    #   - passive voice
    #   - precision asymmetry
    # ========================================================
    try:
        framing = analyze_framing(text)
    except Exception:
        app.logger.exception("Framing analysis failed")
        return error_response(
            500,
            "FRAMING_ANALYSIS_FAILED",
            "Failed to analyze article framing.",
        )

    # ========================================================
    # STEP 3: Fetch related articles
    # [RELATED_ARTICLES_FETCH]
    #
    # IMPORTANT:
    # The actual per-query article limit is controlled by num=10.
    # This is one of the main places to edit if you want more/fewer results.
    #
    # CTRL+F:
    #   [RELATED_ARTICLES_LIMIT]
    # ========================================================
    related_articles = []

    try:
        for query in build_search_queries(title, text):
            related_articles = fetch_related_articles(query, NEWS_API_KEY, num=10)  # [RELATED_ARTICLES_LIMIT]
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

    # ========================================================
    # STEP 4: Embedding stage
    # [EMBEDDING_STAGE]
    #
    # We combine:
    #   user article text
    #   + all related article snippets
    #
    # into one list so they can be encoded in one model call.
    # This is usually faster than encoding each one separately.
    # ========================================================
    related_texts = [
        a["title"] + " " + a["description"]
        for a in related_articles
    ]

    # Limit user text length before embedding for performance.
    all_texts = [text[:2000]] + related_texts

    try:
        all_embeddings = embed_texts(all_texts)
    except Exception:
        app.logger.exception("Embedding stage failed")
        return error_response(
            503,
            "EMBEDDING_UNAVAILABLE",
            "Text embedding service is unavailable.",
        )

    # First embedding belongs to the user article.
    user_embedding = all_embeddings[0]

    # Remaining embeddings belong to related articles.
    related_embeddings = all_embeddings[1:]

    # ========================================================
    # STEP 5: Consistency scoring
    # [CONSISTENCY_SCORE_OUTPUT]
    #
    # This is where the final percentage score is created.
    # ========================================================
    try:
        scores = compute_scores(user_embedding, related_embeddings, related_articles)
    except Exception:
        app.logger.exception("Scoring stage failed")
        return error_response(
            500,
            "SCORING_FAILED",
            "Failed to compute credibility scoring.",
        )

    # Return everything the popup needs to display.
    return jsonify({
        "ok": True,
        "input": {
            "title": title,
            "url": url,
            "wordCount": word_count,
        },
        "score": scores["consistency_score"],  # final 0-100 percentage
        "label": scores["label"],              # human-readable label
        "tone": tone,
        "framing": framing,
        "related": scores["related"],
    })


if __name__ == "__main__":
    # [LOCAL_SERVER_START]
    app.run(host="0.0.0.0", port=PORT)