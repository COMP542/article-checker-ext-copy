
# Run: pip install -r requirements.txt
# After installing, also run this once to download the spaCy language model:
#   python -m spacy download en_core_web_sm

# Command to run: python backend/visualize_similarity.py

import os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

from api.news_controller import fetch_related_articles
from model.embed_text import embed_texts

load_dotenv()

NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")


def build_demo_heatmap(user_title: str, user_text: str, num_articles: int = 6):
    """
    Builds a cosine-similarity heat map using:
    - the user's article
    - several related articles fetched from NewsAPI

    Output:
    - saves a PNG image called similarity_heatmap.png
    """

    if not NEWS_API_KEY:
        raise RuntimeError("Missing NEWSAPI_KEY in environment.")

    # Fetch related articles using the article title
    related_articles = fetch_related_articles(user_title, NEWS_API_KEY, num=num_articles)

    if not related_articles:
        raise RuntimeError("No related articles found.")

    # Build text list for embedding
    labels = ["User Article"]
    texts = [user_text[:2000]]  # same speed cap idea used in app.py

    for i, article in enumerate(related_articles, start=1):
        combined = f"{article.get('title', '')} {article.get('description', '')}".strip()
        texts.append(combined)
        labels.append(f"Related {i}")

    # Embed all texts
    embeddings = embed_texts(texts)

    # Compute full pairwise cosine similarity matrix
    sim_matrix = cosine_similarity(embeddings) * 100

    # Plot heat map
    plt.figure(figsize=(8, 6))
    plt.imshow(sim_matrix, interpolation="nearest")
    plt.colorbar(label="Cosine Similarity (%)")

    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.yticks(range(len(labels)), labels)

    plt.title("Article Similarity Heat Map")
    plt.tight_layout()
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    os.makedirs(ASSETS_DIR, exist_ok=True)

    output_path = os.path.join(ASSETS_DIR, "similarity_heatmap.png")
    plt.savefig(output_path, dpi=300)
    print(f"Saved heat map to: {output_path}")
    plt.show()

    return sim_matrix, labels


if __name__ == "__main__":
    # Replace this with a real article title and article text you want to demo
    demo_title = "Your article title here"
    demo_text = """
    Paste the full article text here.
    This should be the same kind of text your browser extension sends to the backend.
    """

    matrix, labels = build_demo_heatmap(demo_title, demo_text, num_articles=6)

    print("Labels:")
    for label in labels:
        print("-", label)

    print("\nSimilarity matrix:")
    print(np.round(matrix, 1))