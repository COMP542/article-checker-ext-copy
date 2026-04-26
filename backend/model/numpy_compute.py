# backend/model/numpy_compute.py
#
# This file does two things:
#   1. Scores the tone of the user's article (how opinionated vs factual it is)
#   2. Computes how similar the user's article is to the cluster of
#      related articles fetched from NewsAPI
#
# The math here is called "cosine similarity." It measures the angle
# between two vectors — if two articles point in the same direction
# in vector space, they're semantically similar. The closer the angle
# is to 0 degrees, the more similar (score closer to 1.0).
# We multiply by 100 to turn it into a percentage.

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob


def bias_indicators(text: str) -> dict:
    """
    Scores the writing tone of the article using TextBlob.

    subjectivity: how opinionated vs factual the writing is
        0.0 = purely factual (like a wire report)
        1.0 = purely opinionated (like an editorial)

    polarity: the emotional charge of the writing
        -1.0 = very negative tone
         0.0 = neutral
         1.0 = very positive tone

    TextBlob works by looking at individual words and their known
    sentiment scores, then averaging across the whole text.
    We cap at 3000 characters to keep it fast.
    """
    blob = TextBlob(text[:3000])
    return {
        "subjectivity": round(blob.sentiment.subjectivity, 3),
        "polarity":     round(blob.sentiment.polarity, 3),
    }


def flag_outliers(results: list) -> list:
    """
    Marks related articles that are statistically far from the rest
    of the cluster as outliers.

    How it works:
        - We calculate the average similarity score across all related articles
        - We calculate the standard deviation (how spread out the scores are)
        - Any article more than 1.5 standard deviations below the average
          gets flagged as an outlier

    An outlier article is one that covers the same topic but frames it
    very differently from everyone else — which combined with high
    subjectivity can signal spin or bias.

    We need at least 3 articles to meaningfully define an outlier.
    """
    if len(results) < 3:
        for r in results:
            r["outlier"] = False
        return results

    scores    = np.array([r["similarity"] for r in results])
    mean      = float(np.mean(scores))
    std       = float(np.std(scores))
    threshold = mean - (1.5 * std)

    for r in results:
        r["outlier"] = r["similarity"] < threshold

    return results

def consistency_label(score: float) -> str:
    """
    Takes the reported score and returns written explanation of percentage given to user.
    """

    if score >= 80:
        return "Highly consistent"
    elif score >= 50:
        return "Moderately consistent"
    elif score >= 20:
        return "Low consistency"
    else:
        return "Outlier: Significantly differs from other reporting"


def compute_scores(user_embedding, related_embeddings, related_articles: list) -> dict:
    """
    Takes the vectors for the user's article and all related articles,
    and computes:
        - An overall consistency score (user article vs. the cluster average)
        - Individual similarity scores (user article vs. each related article)

    Parameters:
        user_embedding:     1D numpy array — the vector for the user's article
        related_embeddings: 2D numpy array — one row per related article
        related_articles:   list of dicts from fetch_related_articles()

    Returns a dict with the consistency score and a ranked list of articles.
    """

    # The "cluster center" is just the average of all related article vectors.
    # It represents what the "typical" reporting on this topic looks like.
    cluster_center = np.mean(related_embeddings, axis=0, keepdims=True)

    # How similar is the user's article to that average? → consistency score
    consistency = float(
        cosine_similarity([user_embedding], cluster_center)[0][0]
    )

    # How similar is the user's article to each individual related article?
    individual_scores = cosine_similarity([user_embedding], related_embeddings)[0]

    # Build the result list — one entry per related article
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

    # Sort so the most similar article appears first
    results.sort(key=lambda x: x["similarity"], reverse=True)

    # Flag any articles that are statistical outliers
    results = flag_outliers(results)
    consistency_answer = round(consistency * 100, 1)
    label = consistency_label(consistency_answer)

    return {
        "consistency_score": consistency_answer,
        "related": results,
        "label": label,
    }