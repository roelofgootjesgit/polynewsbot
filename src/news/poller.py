"""
News poller — orchestrates all news sources, normalizes, and yields new events.
"""
import logging
from typing import Any

from src.models.events import NormalizedNewsEvent
from src.news.base import NewsSource
from src.news.normalizer import NewsNormalizer
from src.news.rss import create_rss_sources
from src.news.newsapi_source import create_newsapi_source

logger = logging.getLogger(__name__)


class NewsPoller:
    """Polls all configured news sources and produces normalized events."""

    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg
        self._sources: list[NewsSource] = []
        self._normalizer = NewsNormalizer(cfg)

    def setup(self) -> int:
        """Initialize all configured news sources. Returns source count."""
        self._sources = []

        rss_sources = create_rss_sources(self._cfg)
        self._sources.extend(rss_sources)

        newsapi = create_newsapi_source(self._cfg)
        if newsapi:
            self._sources.append(newsapi)

        logger.info("NewsPoller initialized with %d sources", len(self._sources))
        return len(self._sources)

    def poll(self) -> list[NormalizedNewsEvent]:
        """
        Poll all sources once. Returns new (non-duplicate) normalized events.
        Duplicates are filtered out automatically.
        """
        all_events: list[NormalizedNewsEvent] = []

        for source in self._sources:
            try:
                raw_items = source.fetch()
                events = self._normalizer.normalize_batch(raw_items, source.tier)
                new_events = [e for e in events if not e.is_duplicate]
                all_events.extend(new_events)
                logger.debug(
                    "Source %s: %d raw → %d new events",
                    source.name, len(raw_items), len(new_events),
                )
            except Exception:
                logger.exception("Failed to poll source %s", source.name)

        all_events.sort(key=lambda e: e.received_at)

        logger.info(
            "Poll complete: %d new events from %d sources (dedup cache: %d)",
            len(all_events), len(self._sources), self._normalizer.seen_count,
        )
        return all_events

    @property
    def source_count(self) -> int:
        return len(self._sources)

    @property
    def seen_count(self) -> int:
        return self._normalizer.seen_count
