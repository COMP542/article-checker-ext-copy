
# backend/model/embed_text.py
#
# This file loads an AI language model and uses it to convert
# article text into a list of numbers called a "vector" or "embedding".
#
# Why? Because computers can't directly compare two pieces of text -
# but they CAN compare numbers. Articles about the same topic end up
# with similar numbers, so we can measure how "close" or "far apart"
# two articles are just by doing math on their vectors.
#
# The model (all-MiniLM-L6-v2) was pre-trained by Hugging Face on a
# huge amount of text. We don't train it ourselves - we just use it
# as a feature extractor. It auto-downloads (~80MB) on first run
# and is cached locally after that.

from sentence_transformers import SentenceTransformer

# Load the model once when the server starts.
# Each piece of text becomes a vector of 384 numbers.
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list):
    """
    Takes a list of strings and returns a 2D numpy array
    where each row is the vector for one article.

    Shape: (number_of_articles, 384)

    Articles about similar topics will have vectors that are
    mathematically close to each other - that closeness is
    what we measure to compute the consistency score.
    """
    return model.encode(texts, convert_to_numpy=True)