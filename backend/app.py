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
from model.numpy_compute import compute_scores, bias_indicators
from model.framing_analysis import analyze_framing

import os

# Load environment variables from the .env file in this folder.
# This is how we read NEWSAPI_KEY without hardcoding it in the source code.
load_dotenv()

app = Flask(__name__)
CORS(app)  # allows the browser extension to talk to this server

# Read the NewsAPI key from the .env file
NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")


@app.post("/analyze")
def analyze():
    """
    Main endpoint. The extension POSTs JSON with:
        { "title": "...", "url": "...", "text": "..." }

    Returns JSON with the full analysis result.
    """
    data  = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    url   = (data.get("url")   or "").strip()
    text  = (data.get("text")  or "").strip()

    # Can't do anything without article text
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # --- Step 1: Tone analysis ---
    # Scores how opinionated vs factual the writing is, and its emotional charge
    tone = bias_indicators(text)

    # --- Step 2: Framing analysis ---
    # Detects language patterns like selective doubt, passive voice,
    # and precision asymmetry that can indicate one-sided framing
    framing = analyze_framing(text)

    # --- Step 3: Fetch related articles ---
    # Use the article title as the search query (fall back to first 120 chars of text)
    query = title if title else text[:120]
    related_articles = fetch_related_articles(query, NEWS_API_KEY, num=10)

    if not related_articles:
        return jsonify({"error": "No related articles found. Check your NewsAPI key."}), 502

    # --- Step 4: Embed everything as vectors ---
    # Combine the user's article with all related articles into one list,
    # then encode them all at once (faster than encoding separately)
    related_texts = [
        a["title"] + " " + a["description"]
        for a in related_articles
    ]

    all_texts      = [text[:2000]] + related_texts  # cap user text for speed
    all_embeddings = embed_texts(all_texts)

    user_embedding     = all_embeddings[0]   # first row = user's article
    related_embeddings = all_embeddings[1:]  # remaining rows = related articles

    # --- Step 5: Score consistency and rank related articles ---
    scores = compute_scores(user_embedding, related_embeddings, related_articles)

    # Send the full result back to the extension
    return jsonify({
        "ok":    True,
        "input": {
            "title":     title,
            "url":       url,
            "wordCount": len(text.split()),
        },
        "score":   scores["consistency_score"],  # 0-100, how consistent with the cluster
        "tone":    tone,                          # subjectivity + polarity
        "framing": framing,                       # language pattern flags
        "related": scores["related"],             # ranked list of related articles
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)