# ============================================================
# FILE: backend/model/framing_analysis.py
# PURPOSE:
#   Detect language patterns that may indicate framing.
#
# CTRL+F TAGS:
#   [HEDGING_DETECTION]
#   [PASSIVE_VOICE_DETECTION]
#   [PRECISION_ASYMMETRY]
#   [FRAMING_WARNING]
# ============================================================

import re
import spacy

# Load spaCy language model once at startup.
# This model is used for grammatical parsing.
nlp = spacy.load("en_core_web_sm")

# [HEDGING_LEXICON]
DOUBT_VERBS = {
    "claim", "claims",
    "allege", "alleges",
    "insist", "insists",
    "reportedly", "supposedly", "purportedly",
    "assert", "asserts",
    "contend", "contends",
    "maintain", "maintains",
    "suggest", "suggests",
    "according"
}

# [CERTAINTY_LEXICON]
CERTAINTY_VERBS = {
    "confirmed", "revealed", "showed", "proved", "found",
    "demonstrated", "established", "verified", "acknowledged", "admitted"
}

# [VAGUE_LANGUAGE_PATTERN]
VAGUE = r"\b(unconfirmed|unknown|unclear|some|several|many|numerous|multiple|various)\b"

# [PRECISE_NUMBER_PATTERN]
PRECISE = r"\b(\d+)\s*(people|civilians|soldiers|killed|dead|wounded|injured|casualties|victims)\b"


def detect_hedging(text: str) -> dict:
    """
    [HEDGING_DETECTION]
    Counts doubt language and certainty language.

    Idea:
    If an article repeatedly describes one side with words like
    'claims' or 'allegedly' while using stronger certainty for another side,
    that can subtly shape reader perception.
    """
    words = re.findall(r"\b\w+\b", text.lower())

    doubt_found = [w for w in words if w in DOUBT_VERBS]
    certainty_found = [w for w in words if w in CERTAINTY_VERBS]

    doubt_count = len(doubt_found)
    certainty_count = len(certainty_found)

    return {
        "doubt_language_count": doubt_count,
        "certainty_language_count": certainty_count,
        "flag": doubt_count > certainty_count and doubt_count > 0,
        "flagged_words": {
            "doubt": list(set(doubt_found)),
            "certainty": list(set(certainty_found)),
        }
    }


def detect_passive_voice(text: str) -> dict:
    """
    [PASSIVE_VOICE_DETECTION]
    Uses spaCy dependency parsing to estimate passive voice ratio.

    Why passive voice matters:
    It can hide the actor:
      'The building was hit'
      instead of
      'X hit the building'
    """
    doc = nlp(text[:3000])

    passives = sum(1 for token in doc if token.dep_ == "nsubjpass")
    total_verbs = sum(1 for token in doc if token.pos_ == "VERB")

    ratio = round(passives / total_verbs, 3) if total_verbs else 0

    return {
        "passive_voice_ratio": ratio,
        "flag": ratio > 0.3
    }


def detect_precision_asymmetry(text: str) -> dict:
    """
    [PRECISION_ASYMMETRY]
    Looks for both:
      - vague quantity language
      - precise numerical claims

    If both appear together, that may indicate uneven specificity.
    """
    vague_found = re.findall(VAGUE, text.lower())
    precise_found = [" ".join(match) for match in re.findall(PRECISE, text.lower())]

    vague_count = len(vague_found)
    precise_count = len(precise_found)

    return {
        "vague_quantity_count": vague_count,
        "precise_quantity_count": precise_count,
        "flag": vague_count > 0 and precise_count > 0,
        "flagged_words": {
            "doubt": list(set(vague_found)),
            "certainty": list(set(precise_found)),
        }
    }


def analyze_framing(text: str) -> dict:
    """
    [FRAMING_WARNING]
    Runs all framing detectors and combines their flags.

    Final warning rule:
    if 2 or more checks are flagged, framing_warning = True
    """
    hedging = detect_hedging(text)
    passive = detect_passive_voice(text)
    precision = detect_precision_asymmetry(text)

    flags_triggered = sum([
        hedging["flag"],
        passive["flag"],
        precision["flag"]
    ])

    return {
        "hedging": hedging,
        "passive_voice": passive,
        "precision_asymmetry": precision,
        "flags_triggered": flags_triggered,
        "framing_warning": flags_triggered >= 2
    }