
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
from app import build_search_queries

load_dotenv()

NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")

def shorten_label(text: str, max_len: int = 42) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


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
    related_articles = []

    for query in build_search_queries(user_title, user_text):
        print(f"[DEBUG] Trying fallback query: {query}")
        related_articles = fetch_related_articles(query, NEWS_API_KEY, num=num_articles)
        if related_articles:
            break

    if not related_articles:
        raise RuntimeError("No related articles found after trying fallback queries.")

    # Build text list for embedding
    user_short = shorten_label(user_title, 42) or "User article"
    labels = [f"{user_short} [input]"]
    texts = [user_text[:2000]]

    for i, article in enumerate(related_articles, start=1):
        combined = f"{article.get('title', '')} {article.get('description', '')}".strip()
        texts.append(combined)

        source = article.get("source", "Unknown source")
        title = article.get("title", f"Related article {i}")
        short_title = shorten_label(title, 36)

        labels.append(f"{source}: {short_title} [related {i}]")
        

    # Embed all texts
    embeddings = embed_texts(texts)

    # Compute full pairwise cosine similarity matrix
    sim_matrix = cosine_similarity(embeddings) * 100

    # Plot heat map
    plt.figure(figsize=(10, 8))
    plt.imshow(sim_matrix, interpolation="nearest")
    plt.colorbar(label="Cosine Similarity (%)")

    plt.xticks(range(len(labels)), labels, rotation=40, ha="right", fontsize=9)
    plt.yticks(range(len(labels)), labels, fontsize=9)

    for i in range(sim_matrix.shape[0]):
        for j in range(sim_matrix.shape[1]):
            value = sim_matrix[i, j]
            plt.text(
                j, i,
                f"{value:.1f}",
                ha="center",
                va="center",
                color="white" if value < 60 else "black",
                fontsize=9
            )

    plt.title("Pairwise Cosine Similarity of Article Embeddings")
    plt.tight_layout()
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    os.makedirs(ASSETS_DIR, exist_ok=True)

    output_path = os.path.join(ASSETS_DIR, "similarity_heatmap.png")
    plt.savefig(output_path, dpi=300)
    print(f"Saved heat map to: {output_path}")
    plt.show()

    user_embedding = embeddings[0]
    related_embeddings = embeddings[1:]

    cluster_center = np.mean(related_embeddings, axis=0, keepdims=True)
    consistency_score = float(cosine_similarity([user_embedding], cluster_center)[0][0]) * 100

    print(f"Extension-style consistency score: {consistency_score:.1f}%")

    return sim_matrix, labels


if __name__ == "__main__":
    # Replace this with a real article title and article text you want to demo
    demo_title = "Iran school bombing UNESCO"
    demo_text = """
    The missiles reportedly destroyed a girl’s primary school in Minab, southern Iran, killing around 150 and wounding almost 100. Many students are believed to be among the dead.
    In a statement released on social media, UNESCO expressed deep alarm at the impact of the military attacks, which continued into Sunday, and noted that pupils in a place dedicated to learning are protected under international humanitarian law, and that “attacks against educational institutions endanger students and teachers and undermine the right to education.”
    UNESCO joined a host of bodies from across the United Nations system and senior officials, including Secretary-General António Guterres, to condemn the military attacks, as well as the retaliatory strikes by Iran that hit several Middle Eastern countries..
    “The killing of civilians, especially children, is unconscionable, and I condemn it unequivocally,” she said in a social media post, and called for the escalation of violence across the region to end, and for justice and accountability to follow.
    “All states and parties must uphold their obligations under international law to protect civilians and safeguard schools,” she wrote. “Every child deserves to live and learn in peace.”
    Malala became an international symbol of the fight for girls’ education after she was shot in 2012 for opposing Taliban restrictions on female education in her home country of Pakistan.
    """
    

    matrix, labels = build_demo_heatmap(demo_title, demo_text, num_articles=6)

    print("Labels:")
    for label in labels:
        print("-", label)

    print("\nSimilarity matrix:")
    print(np.round(matrix, 1))