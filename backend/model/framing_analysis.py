
# backend/model/framing_analysis.py
#
# This file detects subtle language patterns in an article that can
# indicate biased or asymmetric framing - without ever saying anything
# explicitly false. These are real journalistic techniques used to make
# one side of a story seem more credible than another.
#
# We don't label the article as "biased." We just count the patterns
# and show the user the numbers so they can decide for themselves.
#
# NOTE: Filename is framing_analysis.py (not framing_analysis.py).
# Make sure your actual file on disk matches this spelling.

import re
import spacy

# spaCy is a natural language processing library that can parse
# sentence structure - it understands grammar, not just word counts.
# Run this once in your terminal before using this file:
#   python -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm")


#

# These words cast DOUBT on a statement.
# Example: "Iran claims the strike killed 10 people"
# Using "claims" implies we're not sure if it's true.
DOUBT_VERBS = {
    "claims", "alleges", "insists", "reportedly", "supposedly",
    "purportedly", "asserts", "contends", "maintains", "suggests"
}

# These words assert something is FACTUALLY SETTLED.
# Example: "Israel confirmed the strike killed 10 people" vs "Iran claims 30 people dead"
# Using "confirmed" implies it's an established fact, while claims devalues or downplays the opposition.
CERTAINTY_VERBS = {
    "confirmed", "revealed", "showed", "proved", "found",
    "demonstrated", "established", "verified", "acknowledged", "admitted"
}

# Vague quantity language — hides how many people were affected
VAGUE = r"\b(unconfirmed|unknown|unclear|some|several|many|numerous|multiple|various)\b"

# Precise numerical claims about people — gives an exact count
PRECISE = r"\b(\d+)\s*(people|civilians|soldiers|killed|dead|wounded|injured|casualties|victims)\b"


# --- Detection functions ---

def detect_hedging(text: str) -> dict:
    """
    Counts how often the article uses doubt language vs certainty language.

    If one side of a story gets "claims" and "allegedly" while the other
    side gets "confirmed" and "revealed", that's selective skepticism —
    the article is treating one side's statements as uncertain and the
    other's as fact, which subtly shifts how the reader perceives each side.
    """
    words = re.findall(r"\b\w+\b", text.lower())

    doubt_count = sum(1 for w in words if w in DOUBT_VERBS)
    certainty_count = sum(1 for w in words if w in CERTAINTY_VERBS)

    return {
        "doubt_language_count": doubt_count,
        "certainty_language_count": certainty_count,
        # Flag if there's a lot of doubt language and zero certainty language
        "flag": doubt_count > 3 and certainty_count == 0
    }


def detect_passive_voice(text: str) -> dict:
    """
    Uses spaCy's grammar parser to find passive voice constructions.

    Passive voice removes the actor from a sentence:
      "The building was bombed"  →  who bombed it?
      "Civilians were killed"    →  who killed them?

    A high passive voice ratio can mean the article is systematically
    avoiding naming who did what — which matters a lot in conflict reporting.

    We cap the text at 3000 characters to keep it fast.
    """
    doc = nlp(text[:3000])

    # nsubjpass = passive nominal subject (grammar term for passive voice subject)
    passives = sum(1 for token in doc if token.dep_ == "nsubjpass")
    total_verbs = sum(1 for token in doc if token.pos_ == "VERB")

    ratio = round(passives / total_verbs, 3) if total_verbs else 0

    return {
        "passive_voice_ratio": ratio,
        # Flag if more than 30% of verbs are passive
        "flag": ratio > 0.3
    }


def detect_precision_asymmetry(text: str) -> dict:
    """
    Checks if the article mixes vague quantity language with precise numbers.

    Example of asymmetry:
      "An unconfirmed number of Iranian soldiers were killed"  ← vague
      "Exactly 47 Israeli civilians were wounded"              ← precise

    When one side gets exact numbers and the other gets vague language,
    it creates an implicit imbalance — one side feels more real and documented.
    """
    vague_matches = re.findall(VAGUE, text.lower())
    precise_matches = re.findall(PRECISE, text.lower())

    vague_count = len(vague_matches)
    precise_count = len(precise_matches)

    return {
        "vague_quantity_count": vague_count,
        "precise_quantity_count": precise_count,
        # Flag if both vague AND precise language appear in the same article
        "flag": vague_count > 0 and precise_count > 0
    }


def analyze_framing(text: str) -> dict:
    """
    Runs all three framing checks and returns a combined result.
    This is the function that app.py calls.

    framing_warning = True means 2 or more checks were flagged,
    which is a stronger signal that the article may be framing
    the story in a one-sided way.
    """
    hedging   = detect_hedging(text)
    passive   = detect_passive_voice(text)
    precision = detect_precision_asymmetry(text)

    flags_triggered = sum([
        hedging["flag"],
        passive["flag"],
        precision["flag"]
    ])

    return {
        "hedging":              hedging,
        "passive_voice":        passive,
        "precision_asymmetry":  precision,
        "flags_triggered":      flags_triggered,
        # True if 2 or more of the 3 checks were flagged
        "framing_warning":      flags_triggered >= 2
    }