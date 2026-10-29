"""Fetch and normalize technology news from NewsAPI."""

from datetime import datetime, timezone
from typing import Any, Optional

import requests

import config
from models import categorize_news

NEWS_API_URL = "https://newsapi.org/v2/everything"
TECH_NEWS_QUERY = (
    'technology OR "artificial intelligence" OR "agentic AI" OR '
    '"quantum computing" OR "cloud computing" OR cybersecurity OR '
    'programming OR "developer tools" OR startups'
)
REQUEST_TIMEOUT_SECONDS = 10


class NewsServiceError(Exception):
    """Raised when the news API request or response cannot be used."""


def _parse_published_at(value: Any) -> Optional[datetime]:
    """Convert an ISO 8601 publication date to a datetime when possible."""
    if not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_latest_news() -> list[dict[str, Any]]:
    """Fetch recent technology articles and return normalized documents."""
    if not config.NEWS_API_KEY:
        raise NewsServiceError("NEWS_API_KEY is missing. Add it to your .env file.")
    
    try:
        response = requests.get(
            NEWS_API_URL,
            headers={"X-Api-Key": config.NEWS_API_KEY},
            params={
                "q": TECH_NEWS_QUERY,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 100,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    except requests.exceptions.Timeout as error:
        print("NewsAPI timeout:", str(error))
        raise NewsServiceError(
            "The news API request timed out."
        ) from error

    except requests.exceptions.RequestException as error:
        print("NewsAPI error type:", type(error).__name__)
        print("NewsAPI error details:", str(error))

        if error.response is not None:
            print("HTTP status:", error.response.status_code)
            print("API response:", error.response.text[:500])

        raise NewsServiceError(
            "Could not retrieve news. Check the network and API settings."
        ) from error


    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise NewsServiceError("The news API returned invalid JSON.") from error

    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise NewsServiceError("The news API returned an unsuccessful response.")

    articles = payload.get("articles")
    if not isinstance(articles, list):
        raise NewsServiceError("The news API response did not contain an article list.")

    collected_at = datetime.now(timezone.utc)
    news_documents = []

    for article in articles:
        if not isinstance(article, dict):
            continue

        title = article.get("title")
        url = article.get("url")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(url, str) or not url.strip():
            continue

        description = article.get("description")
        if not isinstance(description, str):
            description = None

        source_data = article.get("source")
        source_name = source_data.get("name") if isinstance(source_data, dict) else None

        author = article.get("author")
        if not isinstance(author, str):
            author = None

        news_documents.append(
            {
                "title": title.strip(),
                "description": description,
                "source": source_name or "Unknown",
                "author": author,
                "url": url.strip(),
                "category": categorize_news(title, description),
                "published_at": _parse_published_at(article.get("publishedAt")),
                "collected_at": collected_at,
            }
        )

    return news_documents
