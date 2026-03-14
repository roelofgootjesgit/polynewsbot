"""Tests for news normalizer and deduplication."""
from datetime import datetime, timezone

from src.models.events import RawNewsItem, SourceTier
from src.news.normalizer import NewsNormalizer, _headline_hash, _extract_topic_hints


def _make_cfg():
    return {"news": {"source_tiers": {
        "tier_1_reliability": 0.95,
        "tier_2_reliability": 0.80,
        "tier_3_reliability": 0.55,
        "tier_4_reliability": 0.25,
    }}}


def test_normalize_basic():
    n = NewsNormalizer(_make_cfg())
    raw = RawNewsItem(
        source_name="Reuters",
        headline="Fed raises rates by 25bps",
        body="The Federal Reserve raised interest rates.",
        url="https://reuters.com/article/1",
        published_at=datetime.now(timezone.utc),
    )
    event = n.normalize(raw, SourceTier.TIER_2_TRUSTED_MEDIA)
    assert event.source_name == "Reuters"
    assert event.source_tier == SourceTier.TIER_2_TRUSTED_MEDIA
    assert event.source_reliability_score == 0.80
    assert event.headline == "Fed raises rates by 25bps"
    assert not event.is_duplicate
    assert event.event_id


def test_deduplication():
    n = NewsNormalizer(_make_cfg())
    raw1 = RawNewsItem(source_name="Reuters", headline="Bitcoin hits $100k")
    raw2 = RawNewsItem(source_name="AP", headline="Bitcoin hits $100k")
    raw3 = RawNewsItem(source_name="BBC", headline="Ethereum surges 20%")

    e1 = n.normalize(raw1, SourceTier.TIER_2_TRUSTED_MEDIA)
    e2 = n.normalize(raw2, SourceTier.TIER_2_TRUSTED_MEDIA)
    e3 = n.normalize(raw3, SourceTier.TIER_2_TRUSTED_MEDIA)

    assert not e1.is_duplicate
    assert e2.is_duplicate
    assert e2.duplicate_of == e1.event_id
    assert not e3.is_duplicate


def test_dedup_case_insensitive():
    n = NewsNormalizer(_make_cfg())
    raw1 = RawNewsItem(source_name="A", headline="FED RAISES RATES")
    raw2 = RawNewsItem(source_name="B", headline="fed raises rates")
    e1 = n.normalize(raw1, SourceTier.TIER_2_TRUSTED_MEDIA)
    e2 = n.normalize(raw2, SourceTier.TIER_2_TRUSTED_MEDIA)
    assert not e1.is_duplicate
    assert e2.is_duplicate


def test_normalize_batch():
    n = NewsNormalizer(_make_cfg())
    items = [
        RawNewsItem(source_name="A", headline="News item 1"),
        RawNewsItem(source_name="A", headline="News item 2"),
        RawNewsItem(source_name="A", headline="News item 1"),  # dup
    ]
    events = n.normalize_batch(items, SourceTier.TIER_2_TRUSTED_MEDIA)
    assert len(events) == 3
    assert not events[0].is_duplicate
    assert not events[1].is_duplicate
    assert events[2].is_duplicate


def test_topic_extraction():
    assert "crypto" in _extract_topic_hints("Bitcoin surges past $100k")
    assert "central_banks" in _extract_topic_hints("Fed raises interest rate by 50bps")
    assert "politics" in _extract_topic_hints("Trump wins election")
    assert "economics" in _extract_topic_hints("US CPI inflation data released")
    assert "regulation" in _extract_topic_hints("SEC approves new crypto ETF")
    assert _extract_topic_hints("Weather is nice today") == []


def test_tier_reliability_scores():
    n = NewsNormalizer(_make_cfg())
    raw = RawNewsItem(source_name="test", headline="test")

    e1 = n.normalize(raw, SourceTier.TIER_1_PRIMARY)
    assert e1.source_reliability_score == 0.95

    n.reset_seen()
    e4 = n.normalize(raw, SourceTier.TIER_4_RUMOR)
    assert e4.source_reliability_score == 0.25


def test_headline_hash_deterministic():
    h1 = _headline_hash("Fed raises rates")
    h2 = _headline_hash("Fed raises rates")
    h3 = _headline_hash("Fed lowers rates")
    assert h1 == h2
    assert h1 != h3
