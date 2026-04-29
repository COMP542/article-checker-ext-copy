# ============================================================
# FILE: backend/model/embed_text.py
# PURPOSE:
#   Convert article text into numeric embeddings for similarity math.
#
# CTRL+F TAGS:
#   [EMBED_MODEL]
#   [VECTOR_DIMENSIONS]
#   [EMBED_BATCH]
# ============================================================

from sentence_transformers import SentenceTransformer

# [EMBED_MODEL]
# Load once at startup so repeated requests are faster.
# all-MiniLM-L6-v2 outputs embeddings with 384 dimensions.
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list):
    """
    [EMBED_BATCH] [VECTOR_DIMENSIONS]

    Encode a list of text strings into a 2D numpy array.

    Input:
      ["article text 1", "article text 2", ...]

    Output shape:
      (number_of_texts, 384)

    Why this matters:
    Similar articles will produce embeddings that are closer together
    in vector space, which lets us compare them numerically.
    """
    return model.encode(texts, convert_to_numpy=True)