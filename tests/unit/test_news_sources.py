"""Tests for news source implementations."""
from unittest.mock import patch, MagicMock

from src.news.rss import RSSSource, create_rss_sources, _parse_entry
from src.models.events import SourceTier


def test_rss_source_properties():
    src = RSSSource("Reuters", "https://feeds.reuters.com/rss", tier=2)
    assert src.name == "Reuters"
    assert src.tier == SourceTier.TIER_2_TRUSTED_MEDIA


def test_parse_rss_entry():
    entry = {
        "title": "Fed raises rates by 25bps",
        "summary": "The Federal Reserve announced...",
        "link": "https://example.com/article",
        "published_parsed": (2026, 3, 14, 12, 0, 0, 0, 0, 0),
    }
    item = _parse_entry(entry, "TestFeed")
    assert item is not None
    assert item.headline == "Fed raises rates by 25bps"
    assert item.source_name == "TestFeed"
    assert item.url == "https://example.com/article"
    assert item.published_at is not None


def test_parse_rss_entry_empty_title():
    assert _parse_entry({"title": "", "link": ""}, "X") is None
    assert _parse_entry({"link": ""}, "X") is None


def test_create_rss_sources_from_config():
    cfg = {"news": {"sources": {"rss": {
        "enabled": True,
        "feeds": [
            {"name": "Reuters", "url": "https://feeds.reuters.com/rss", "tier": 2},
            {"name": "CoinDesk", "url": "https://coindesk.com/rss", "tier": 2},
        ],
    }}}}
    sources = create_rss_sources(cfg)
    assert len(sources) == 2
    assert sources[0].name == "Reuters"
    assert sources[1].name == "CoinDesk"


def test_create_rss_sources_disabled():
    cfg = {"news": {"sources": {"rss": {"enabled": False, "feeds": []}}}}
    assert create_rss_sources(cfg) == []
