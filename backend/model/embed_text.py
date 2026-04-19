# backend/model/embed_text.py

from sentence_transformers import SentenceTransformer

# all-MiniLM-L6-v2 is small (~80MB), fast, and accurate enough for this use case.
# It will auto-download on first run and cache locally after that.
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_texts(texts: list) -> object:
    """
    Takes a list of strings and returns a numpy array
    of shape (n_texts, 384) — each text becomes a 384-dimensional
    point in vector space. Texts about the same topic cluster together.
    """
    return model.encode(texts, convert_to_numpy=True)