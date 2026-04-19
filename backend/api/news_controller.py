# backend/api/news_controller.py

# backend/api/news_controller.py

import requests

OWNERSHIP_LABELS = {
    # Wire services — least editorialized
    "Reuters": "wire",
    "Associated Press": "wire",
    "AFP": "wire",

    # Corporate — owned by large conglomerates
    "CNN": "corporate",  # Warner Bros. Discovery
    "Fox News": "corporate",  # News Corp
    "MSNBC": "corporate",  # Comcast/NBCUniversal
    "NBC News": "corporate",  # Comcast/NBCUniversal
    "ABC News": "corporate",  # Disney
    "CBS News": "corporate",  # Paramount Global
    "The Wall Street Journal": "corporate",  # News Corp
    "New York Post": "corporate",  # News Corp
    "HuffPost": "corporate",  # BuzzFeed Inc
    "Business Insider": "corporate",  # Axel Springer
    "Politico": "corporate",  # Axel Springer

    # State-funded
    "BBC News": "state",
    "NPR": "state",
    "PBS": "state",
    "Al Jazeera English": "state",
    "RT": "state",
    "Voice of America": "state",

    # Tabloid — sensationalism-first
    "Daily Mail": "tabloid",
    "The Sun": "tabloid",
    "New York Daily News": "tabloid",
    "TMZ": "tabloid",

    # Independent — not owned by a major conglomerate
    "The Guardian": "independent",
    "The Intercept": "independent",
    "ProPublica": "independent",
    "Reason": "independent",
    "The Hill": "independent",
}


def get_ownership_label(source_name: str) -> str:
    return OWNERSHIP_LABELS.get(source_name, "unknown")


def fetch_related_articles(query: str, api_key: str, num: int = 10) -> list:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": num,
        "apiKey": api_key,
    }

    response = requests.get(url, params=params)
    articles = response.json().get("articles", [])

    return [
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
