"""Tests for relevance filter."""
import uuid
from datetime import datetime, timezone, timedelta

from src.models.events import NormalizedNewsEvent, SourceTier
from src.filter.relevance import RelevanceFilter


def _make_cfg(**overrides):
    cfg = {"filter": {
        "min_relevance_score": 0.5,
        "max_age_minutes": 15,
        "categories": ["crypto", "politics", "economics", "central_banks", "regulation"],
        "keywords_whitelist": [],
        "keywords_blacklist": ["sports", "nba", "nfl"],
    }}
    cfg["filter"].update(overrides)
    return cfg


def _make_event(headline="Test", topics=None, published_at=None, tier=2, is_dup=False):
    return NormalizedNewsEvent(
        event_id=str(uuid.uuid4()),
        received_at=datetime.now(timezone.utc),
        published_at=published_at or datetime.now(timezone.utc),
        source_name="Test",
        source_tier=SourceTier(tier),
        source_reliability_score=0.8,
        headline=headline,
        topic_hints=topics or [],
        is_duplicate=is_dup,
    )


def test_relevant_crypto_news():
    f = RelevanceFilter(_make_cfg())
    event = _make_event("Bitcoin surges past $100k", topics=["crypto"])
    result = f.check(event)
    assert result.passed
    assert result.score > 0.5


def test_irrelevant_sports_blacklisted():
    f = RelevanceFilter(_make_cfg())
    event = _make_event("NBA finals game 7 results", topics=[])
    result = f.check(event)
    assert not result.passed
    assert result.semantic_score == 0.0


def test_duplicate_filtered():
    f = RelevanceFilter(_make_cfg())
    event = _make_event("Something", is_dup=True)
    result = f.check(event)
    assert not result.passed
    assert "duplicate" in result.reasons


def test_old_news_low_time_score():
    f = RelevanceFilter(_make_cfg())
    old_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    event = _make_event("Fed raises rates", topics=["central_banks"], published_at=old_time)
    result = f.check(event)
    assert result.time_score == 0.0


def test_fresh_news_high_time_score():
    f = RelevanceFilter(_make_cfg())
    fresh = datetime.now(timezone.utc) - timedelta(minutes=1)
    event = _make_event("Fed raises rates", topics=["central_banks"], published_at=fresh)
    result = f.check(event)
    assert result.time_score > 0.8


def test_no_topic_low_score():
    f = RelevanceFilter(_make_cfg())
    event = _make_event("Random headline with no topic matches")
    result = f.check(event)
    assert result.semantic_score < 0.5


def test_whitelist_override():
    f = RelevanceFilter(_make_cfg(keywords_whitelist=["urgent"]))
    event = _make_event("URGENT: Major development")
    result = f.check(event)
    assert result.semantic_score == 1.0


def test_filter_batch():
    f = RelevanceFilter(_make_cfg())
    events = [
        _make_event("Bitcoin hits $200k", topics=["crypto"]),
        _make_event("NBA scores tonight", topics=[]),
        _make_event("Fed meeting results", topics=["central_banks"]),
    ]
    passed = f.filter_batch(events)
    assert len(passed) >= 1  # at least crypto + fed should pass
