# ============================================================
# FILE: backend/api/news_controller.py
# PURPOSE:
#   Talks to NewsAPI and returns related articles.
#
# CTRL+F TAGS:
#   [NEWSAPI_FETCH]
#   [ARTICLE_LIMIT]
#   [OWNERSHIP_LABELS]
#   [SOURCE_CATEGORY]
#   [UPSTREAM_RESPONSE]
# ============================================================

import requests

# [OWNERSHIP_LABELS]
# Maps outlet names to simplified ownership categories.
# This is metadata for user context, not a truth score.
OWNERSHIP_LABELS = {
    "Reuters": "wire",
    "Associated Press": "wire",
    "AFP": "wire",

    "CNN": "corporate",
    "Fox News": "corporate",
    "MSNBC": "corporate",
    "NBC News": "corporate",
    "ABC News": "corporate",
    "CBS News": "corporate",
    "The Wall Street Journal": "corporate",
    "New York Post": "corporate",
    "HuffPost": "corporate",
    "Business Insider": "corporate",
    "Politico": "corporate",

    "BBC News": "state",
    "NPR": "state",
    "PBS": "state",
    "Al Jazeera English": "state",
    "RT": "state",
    "Voice of America": "state",

    "Daily Mail": "tabloid",
    "The Sun": "tabloid",
    "New York Daily News": "tabloid",
    "TMZ": "tabloid",

    "The Guardian": "independent",
    "The Intercept": "independent",
    "ProPublica": "independent",
    "Reason": "independent",
    "The Hill": "independent",
}


def get_ownership_label(source_name: str) -> str:
    """
    [SOURCE_CATEGORY]
    Return ownership category for a given outlet name.
    Defaults to 'unknown' if the source is not in the lookup table.
    """
    return OWNERSHIP_LABELS.get(source_name, "unknown")


def fetch_related_articles(query: str, api_key: str, num: int = 10) -> list:
    """
    [NEWSAPI_FETCH] [ARTICLE_LIMIT]

    Search NewsAPI for related articles.

    Parameters:
      query:
        search phrase, usually based on the title
      api_key:
        NewsAPI authentication key
      num:
        how many articles to request from NewsAPI

    IMPORTANT:
      This 'num' value is one of the main controls for
      how many related articles the app gathers.

    Returns:
      A list of simplified article dictionaries ready for scoring.
    """
    print(f"[DEBUG] fetch_related_articles called with query: '{query}', api_key exists: {bool(api_key)}")

    # Reject blank queries early.
    if not query or not query.strip():
        print("[DEBUG] Empty query provided")
        return []

    url = "https://newsapi.org/v2/everything"

    # [UPSTREAM_REQUEST_PARAMS]
    params = {
        "q": query,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": num,   # [ARTICLE_LIMIT]
        "apiKey": api_key,
    }

    print(f"[DEBUG] Making NewsAPI request with params: {params}")

    try:
        response = requests.get(url, params=params)
        print(f"[DEBUG] NewsAPI response status: {response.status_code}")
    except Exception as e:
        print(f"[DEBUG] Exception making NewsAPI request: {e}")
        return []

    if response.status_code != 200:
        print(f"[DEBUG] NewsAPI error: {response.status_code} - {response.text}")
        return []

    try:
        data = response.json()
        articles = data.get("articles", [])
        print(f"[DEBUG] NewsAPI returned {len(articles)} articles")
    except Exception as e:
        print(f"[DEBUG] Exception parsing NewsAPI response: {e}")
        return []

    result = [
        {
            "title": article.get("title"),
            "description": article.get("description") or "",
            "url": article.get("url"),
            "source": article["source"]["name"],
            "ownership": get_ownership_label(article["source"]["name"]),
            "publishedAt": article.get("publishedAt"),
        }
        for article in articles
        if article.get("title")
    ]

    print(f"[DEBUG] Returning {len(result)} processed articles")
    return result