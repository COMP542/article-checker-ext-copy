# ============================================================
# FILE: backend/model/numpy_compute.py
# PURPOSE:
#   Numeric scoring logic for:
#     1) tone indicators
#     2) related-article similarity
#     3) overall consistency percentage
#     4) outlier detection
#
# CTRL+F TAGS:
#   [PERCENTAGE_SCORE]
#   [CONSISTENCY_LABEL]
#   [COSINE_SIMILARITY]
#   [OUTLIER_THRESHOLD]
#   [SUBJECTIVITY_SCORE]
#   [POLARITY_SCORE]
# ============================================================

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob


def bias_indicators(text: str) -> dict:
    """
    [SUBJECTIVITY_SCORE] [POLARITY_SCORE]

    Uses TextBlob sentiment analysis to estimate writing tone.

    Returns:
      - subjectivity:
          0.0 = more factual / neutral-sounding
          1.0 = more opinionated / interpretive
      - polarity:
         -1.0 = negative tone
          0.0 = neutral tone
          1.0 = positive tone

    Important:
    This does NOT verify truth.
    It only measures the emotional / opinionated style of the wording.

    Performance note:
    We cap text to first 3000 characters to keep response time lower.
    """
    blob = TextBlob(text[:3000])

    return {
        "subjectivity": round(blob.sentiment.subjectivity, 3),
        "polarity": round(blob.sentiment.polarity, 3),
    }


def flag_outliers(results: list) -> list:
    """
    [OUTLIER_THRESHOLD]

    Marks articles whose similarity score is much lower than the rest.

    Logic:
      - compute mean similarity
      - compute standard deviation
      - anything below mean - 1.5 * std is marked as an outlier

    Why:
    If most articles cluster together but one article is much farther away,
    that article may be framing or describing the event differently.

    Note:
    We require at least 3 articles to make this meaningful.
    """
    if len(results) < 3:
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


def consistency_label(score: float) -> str:
    """
    [CONSISTENCY_LABEL]

    Converts the numeric percentage score into a readable label.

    Thresholds:
      80+  -> Highly consistent
      50+  -> Moderately consistent
      20+  -> Low consistency
      <20  -> Outlier
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
    [PERCENTAGE_SCORE] [COSINE_SIMILARITY]

    This is the main numeric scoring function.

    Inputs:
      - user_embedding:
          vector for the user's article
      - related_embeddings:
          vectors for all related articles
      - related_articles:
          article metadata from NewsAPI

    What it computes:
      1) cluster center of related article embeddings
      2) cosine similarity between user article and cluster center
      3) cosine similarity between user article and each related article
      4) sorted related-article ranking
      5) outlier flags
      6) human-readable label

    Final percentage:
      cosine similarity returns a value near 0.0 to 1.0
      multiplying by 100 turns it into a percentage-like score
    """

    # --------------------------------------------------------
    # Build the "cluster center"
    # --------------------------------------------------------
    # This is the average vector of the related articles.
    # It acts like the central semantic summary of the reporting cluster.
    cluster_center = np.mean(related_embeddings, axis=0, keepdims=True)

    # --------------------------------------------------------
    # [PERCENTAGE_SCORE]
    # Compute how close the user's article is to the cluster center.
    # This becomes the overall consistency score.
    # --------------------------------------------------------
    consistency = float(
        cosine_similarity([user_embedding], cluster_center)[0][0]
    )

    # --------------------------------------------------------
    # Compute similarity against each individual related article.
    # --------------------------------------------------------
    individual_scores = cosine_similarity([user_embedding], related_embeddings)[0]

    # --------------------------------------------------------
    # Build frontend-ready result records.
    # --------------------------------------------------------
    results = []
    for i, article in enumerate(related_articles):
        results.append({
            "title": article.get("title"),
            "url": article.get("url"),
            "source": article.get("source"),
            "ownership": article.get("ownership", "unknown"),
            "publishedAt": article.get("publishedAt"),
            "similarity": round(float(individual_scores[i]) * 100, 1),  # individual % score
        })

    # Highest similarity appears first.
    results.sort(key=lambda x: x["similarity"], reverse=True)

    # Mark unusually different articles.
    results = flag_outliers(results)

    # Convert overall similarity to display percentage.
    consistency_answer = round(consistency * 100, 1)

    # Convert percentage into explanation label.
    label = consistency_label(consistency_answer)

    return {
        "consistency_score": consistency_answer,
        "related": results,
        "label": label,
    }