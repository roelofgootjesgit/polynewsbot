"""
NewsAPI source — fetches top headlines via newsapi.org.
Requires a free API key (set NEWSAPI_KEY in .env).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from src.models.events import RawNewsItem, SourceTier
from src.news.base import NewsSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://newsapi.org/v2"


class NewsAPISource(NewsSource):
    """Fetches top headlines from NewsAPI."""

    def __init__(self, api_key: str, categories: list[str] | None = None, language: str = "en"):
        self._api_key = api_key
        self._categories = categories or ["general"]
        self._language = language
        self._http = httpx.Client(
            base_url=_BASE_URL,
            timeout=15.0,
            headers={"X-Api-Key": api_key},
        )

    @property
    def name(self) -> str:
        return "NewsAPI"

    @property
    def tier(self) -> SourceTier:
        return SourceTier.TIER_2_TRUSTED_MEDIA

    def fetch(self) -> list[RawNewsItem]:
        """Fetch top headlines across configured categories."""
        all_items: list[RawNewsItem] = []
        for category in self._categories:
            items = self._fetch_category(category)
            all_items.extend(items)
        logger.debug("NewsAPI: fetched %d items across %d categories", len(all_items), len(self._categories))
        return all_items

    def _fetch_category(self, category: str) -> list[RawNewsItem]:
        try:
            resp = self._http.get("/top-headlines", params={
                "category": category,
                "language": self._language,
                "pageSize": 20,
            })
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.warning("NewsAPI: failed to fetch category %s", category)
            return []

        items: list[RawNewsItem] = []
        for article in data.get("articles", []):
            item = _parse_article(article)
            if item:
                items.append(item)
        return items

    def close(self) -> None:
        self._http.close()


def _parse_article(article: dict[str, Any]) -> Optional[RawNewsItem]:
    """Parse a NewsAPI article into a RawNewsItem."""
    title = (article.get("title") or "").strip()
    if not title or title == "[Removed]":
        return None

    source_name = article.get("source", {}).get("name", "NewsAPI")
    body = article.get("description") or article.get("content")
    url = article.get("url")

    published_at = None
    pub_str = article.get("publishedAt")
    if pub_str:
        try:
            published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    return RawNewsItem(
        source_name=source_name,
        headline=title,
        body=body,
        url=url,
        published_at=published_at,
        raw_data={"newsapi_source": source_name},
    )


def create_newsapi_source(cfg: dict[str, Any]) -> Optional[NewsAPISource]:
    """Create NewsAPI source from config (returns None if not configured)."""
    news_cfg = cfg.get("news", {})
    sources_cfg = news_cfg.get("sources", {})
    api_cfg = sources_cfg.get("newsapi", {})

    if not api_cfg.get("enabled", False):
        return None

    api_key = news_cfg.get("newsapi_key", "")
    if not api_key:
        logger.warning("NewsAPI enabled but no API key configured")
        return None

    return NewsAPISource(
        api_key=api_key,
        categories=api_cfg.get("categories", ["general"]),
        language=api_cfg.get("language", "en"),
    )
