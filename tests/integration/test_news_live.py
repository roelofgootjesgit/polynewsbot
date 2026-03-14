"""
Integration tests — fetches real RSS feeds.
Requires internet access.
"""
import pytest

from src.config.loader import load_config
from src.news.poller import NewsPoller

pytestmark = pytest.mark.integration


class TestNewsPollerLive:
    """Tests that fetch real RSS feeds."""

    def test_poll_rss_feeds(self):
        cfg = load_config()
        poller = NewsPoller(cfg)
        count = poller.setup()
        assert count >= 1, "Expected at least 1 RSS source from default config"

        events = poller.poll()
        assert isinstance(events, list)
        # RSS feeds should return something (unless feeds are down)
        if events:
            e = events[0]
            assert e.headline
            assert e.source_name
            assert e.event_id
            assert not e.is_duplicate

    def test_second_poll_deduplicates(self):
        cfg = load_config()
        poller = NewsPoller(cfg)
        poller.setup()

        first = poller.poll()
        second = poller.poll()

        # Second poll should have fewer or equal new events (dedup kicks in)
        # RSS feeds with etag support may return 0 on second call
        assert len(second) <= len(first) or len(second) == 0
