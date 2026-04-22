
# backend/api/news_controller.py
#
# This file handles fetching related articles from NewsAPI.
# It takes the title of the article the user is reading, searches
# for up to 10 recent articles on the same topic, and returns them
# with metadata including an ownership label for each source.
#
# We use ownership labels instead of left/right political ratings
# because outlet ownership (corporate, state, independent, etc.)
# is a structural fact — it describes who controls the outlet and
# what their incentives might be, without implying a political team.

import requests

# A lookup table mapping news source names to their ownership type.
# If a source isn't in this list it gets labeled "unknown."
# You can keep adding sources here as you encounter them in results.
OWNERSHIP_LABELS = {

    # Wire services — raw newswire, typically the least editorialized.
    # These report facts with minimal commentary.
    "Reuters": "wire",
    "Associated Press": "wire",
    "AFP": "wire",

    # Corporate — owned by large conglomerates.
    # Their editorial decisions can reflect the interests of their parent company.
    "CNN": "corporate",                    # Warner Bros. Discovery
    "Fox News": "corporate",               # News Corp
    "MSNBC": "corporate",                  # Comcast / NBCUniversal
    "NBC News": "corporate",               # Comcast / NBCUniversal
    "ABC News": "corporate",               # Disney
    "CBS News": "corporate",               # Paramount Global
    "The Wall Street Journal": "corporate", # News Corp
    "New York Post": "corporate",          # News Corp
    "HuffPost": "corporate",               # BuzzFeed Inc
    "Business Insider": "corporate",       # Axel Springer
    "Politico": "corporate",               # Axel Springer

    # State-funded - funded by a government, fully or partially.
    # Not inherently biased, but worth knowing.
    "BBC News": "state",
    "NPR": "state",
    "PBS": "state",
    "Al Jazeera English": "state",
    "RT": "state",
    "Voice of America": "state",

    # Tabloid - sensationalism and engagement-driven headlines first.
    "Daily Mail": "tabloid",
    "The Sun": "tabloid",
    "New York Daily News": "tabloid",
    "TMZ": "tabloid",

    # Independent - not owned by a major conglomerate or government.
    "The Guardian": "independent",
    "The Intercept": "independent",
    "ProPublica": "independent",
    "Reason": "independent",
    "The Hill": "independent",
}


def get_ownership_label(source_name: str) -> str:
    """Looks up a source name and returns its ownership category."""
    return OWNERSHIP_LABELS.get(source_name, "unknown")


def fetch_related_articles(query: str, api_key: str, num: int = 10) -> list:
    """
    Searches NewsAPI for articles related to the given query string.
    The query is usually the title of the article the user is reading.

    Returns a list of dicts, each containing:
        title, description, url, source name, ownership label, publishedAt
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q":        query,
        "language": "en",
        "sortBy":   "relevancy",  # most relevant articles first
        "pageSize": num,
        "apiKey":   api_key,
    }

    response = requests.get(url, params=params)
    articles = response.json().get("articles", [])

    return [
        {
            "title":       article.get("title"),
            "description": article.get("description") or "",
            "url":         article.get("url"),
            "source":      article["source"]["name"],
            "ownership":   get_ownership_label(article["source"]["name"]),
            "publishedAt": article.get("publishedAt"),
        }
        for article in articles
        if article.get("title")  # skip any results with no title
    ]