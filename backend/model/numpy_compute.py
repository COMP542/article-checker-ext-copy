

# backend/model/numpy_compute.py

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob


def bias_indicators(text: str) -> dict:
    """
    Uses TextBlob to score the writing tone of an article.

    subjectivity: 0.0 = very objective/factual, 1.0 = very subjective/opinionated
    polarity:    -1.0 = very negative tone,     1.0 = very positive tone

    Wire reports (Reuters, AP) typically score below 0.2 subjectivity.
    Heavily editorialized articles often score 0.5+.
    """
    blob = TextBlob(text[:3000])  # cap length for speed
    return {
        "subjectivity": round(blob.sentiment.subjectivity, 3),
        "polarity": round(blob.sentiment.polarity, 3),
    }


def flag_outliers(results: list) -> list:
    """
    Marks articles whose similarity score is more than 1.5 standard
    deviations below the cluster mean as outliers.
    An outlier + high subjectivity is a strong signal of spin or bias.
    """
    if len(results) < 3:
        # not enough articles to meaningfully define an outlier
        for r in results:
            r["outlier"] = False
        return results

    scores = np.array([r["similarity"] for r in results])
    mean = float(np.mean(scores))
    std = float(np.std(scores))
    threshold = mean - (1.5 * std)

    for r in results:
        r["outlier"] = r["similarity"] < threshold

    return results


def compute_scores(user_embedding, related_embeddings, related_articles: list) -> dict:
    """
    user_embedding:     1D numpy array for the user's article
    related_embeddings: 2D numpy array, one row per related article
    related_articles:   list of dicts from fetch_related_articles()

    Returns the overall consistency score and a ranked list of
    related articles with individual similarity scores.
    """
    # Cluster center = mean vector of all related articles
    cluster_center = np.mean(related_embeddings, axis=0, keepdims=True)

    # How similar is the user's article to the overall cluster?
    consistency = float(
        cosine_similarity([user_embedding], cluster_center)[0][0]
    )

    # How similar is the user's article to each individual related article?
    individual_scores = cosine_similarity([user_embedding], related_embeddings)[0]

    # Build result list
    results = []
    for i, article in enumerate(related_articles):
        results.append({
            "title":       article.get("title"),
            "url":         article.get("url"),
            "source":      article.get("source"),
            "ownership":   article.get("ownership", "unknown"),
            "publishedAt": article.get("publishedAt"),
            "similarity":  round(float(individual_scores[i]) * 100, 1),
        })

    # Sort highest similarity first
    results.sort(key=lambda x: x["similarity"], reverse=True)

    # Flag outliers based on similarity distance
    results = flag_outliers(results)

    return {
        "consistency_score": round(consistency * 100, 1),
        "related": results,
    }