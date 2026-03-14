"""Tests for resolution parser."""
import uuid
from datetime import datetime, timezone

from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.markets import MarketCandidate
from src.resolution.parser import ResolutionParser, _extract_key_phrases, _detect_resolution_type


def _make_cfg():
    return {"resolution": {"min_understanding_confidence": 0.7}}


def _make_market(title, resolution_text, deadline=None):
    return MarketCandidate(
        market_id="m1", condition_id="c1",
        market_title=title,
        resolution_text=resolution_text,
        deadline=deadline,
        liquidity_score=0.5,
    )


def _make_event(headline, body=None, tier=2):
    return NormalizedNewsEvent(
        event_id=str(uuid.uuid4()),
        received_at=datetime.now(timezone.utc),
        source_name="Test",
        source_tier=SourceTier(tier),
        source_reliability_score=0.8,
        headline=headline,
        raw_text=body,
    )


def test_parse_criteria_binary():
    parser = ResolutionParser(_make_cfg())
    market = _make_market(
        "Will the Fed raise rates?",
        'This market will resolve to "Yes" if the Federal Reserve announces a rate increase.',
    )
    criteria = parser.parse_criteria(market)
    assert len(criteria.key_phrases) > 0
    assert criteria.confidence > 0.3


def test_parse_criteria_threshold():
    parser = ResolutionParser(_make_cfg())
    market = _make_market(
        "Bitcoin above $100k?",
        "Resolves YES if Bitcoin exceeds $100,000 by December 31, 2026.",
    )
    criteria = parser.parse_criteria(market)
    assert criteria.has_deadline
    assert criteria.resolution_type in ("threshold", "date")


def test_match_event_good():
    parser = ResolutionParser(_make_cfg())
    market = _make_market(
        "Will the Fed raise rates?",
        'This market will resolve to "Yes" if the Federal Reserve announces a rate increase at the next FOMC meeting.',
    )
    criteria = parser.parse_criteria(market)
    event = _make_event(
        "Federal Reserve announces 25bps rate increase",
        body="The Fed confirmed an announce of a rate increase at today's FOMC meeting.",
    )
    match = parser.match_event(event, criteria)
    assert match.match_score > 0.0
    assert len(match.reasoning) > 0


def test_match_event_poor():
    parser = ResolutionParser(_make_cfg())
    market = _make_market(
        "Will BTC hit $200k?",
        "Resolves YES if Bitcoin price exceeds $200,000.",
    )
    criteria = parser.parse_criteria(market)
    event = _make_event("Apple releases new iPhone model")
    match = parser.match_event(event, criteria)
    assert match.match_score < 0.5
    assert not match.sufficient_for_trade


def test_official_source_penalty():
    parser = ResolutionParser(_make_cfg())
    market = _make_market(
        "Will X be officially announced?",
        "Resolves YES if the government officially announces the policy.",
    )
    criteria = parser.parse_criteria(market)
    assert criteria.requires_official_source

    # Tier 4 rumor should get penalized
    event = _make_event("Rumor: policy might be announced soon", tier=4)
    match = parser.match_event(event, criteria)
    # Score should be lower due to source penalty
    assert match.match_score < 0.8


def test_detect_resolution_types():
    assert _detect_resolution_type("resolves yes if price exceeds $100,000") == "threshold"
    assert _detect_resolution_type("price reach above $50") == "threshold"
    assert _detect_resolution_type("who will win the election") == "multi_outcome"
    assert _detect_resolution_type("by march 15 the deadline passes") == "date"


def test_extract_key_phrases():
    text = 'This market will resolve to "Yes" if the SEC approves a spot Bitcoin ETF.'
    phrases = _extract_key_phrases(text)
    assert len(phrases) > 0
    assert any("approve" in p for p in phrases)
