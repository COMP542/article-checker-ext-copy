


# backend/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from api.news_controller import fetch_related_articles
from model.embed_text import embed_texts
from model.numpy_compute import compute_scores, bias_indicators

import os

load_dotenv()

app = Flask(__name__)
CORS(app)

NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")


@app.post("/analyze")
def analyze():
    data  = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    url   = (data.get("url")   or "").strip()
    text  = (data.get("text")  or "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # --- 1. Bias indicators on the user's article ---
    tone = bias_indicators(text)

    # --- 2. Fetch related articles from NewsAPI ---
    query = title if title else text[:120]
    related_articles = fetch_related_articles(query, NEWS_API_KEY, num=10)

    if not related_articles:
        return jsonify({"error": "No related articles found. Check your NewsAPI key."}), 502

    # --- 3. Embed user article + all related articles ---
    related_texts = [
        a["title"] + " " + a["description"]
        for a in related_articles
    ]

    all_texts      = [text[:2000]] + related_texts   # cap user text length for speed
    all_embeddings = embed_texts(all_texts)

    user_embedding     = all_embeddings[0]
    related_embeddings = all_embeddings[1:]

    # --- 4. Compute consistency score + per-article scores ---
    scores = compute_scores(user_embedding, related_embeddings, related_articles)

    return jsonify({
        "ok": True,
        "input": {
            "title":     title,
            "url":       url,
            "wordCount": len(text.split()),
        },
        "tone": tone,            # subjectivity + polarity of the user's article
        "score": scores["consistency_score"],
        "related": scores["related"],
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)