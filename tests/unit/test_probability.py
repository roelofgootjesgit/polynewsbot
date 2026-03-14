"""Tests for the probability engine."""
from datetime import datetime, timezone

from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.markets import MarketCandidate
from src.probability.engine import ProbabilityEngine, _detect_direction, _calculate_shift
from src.resolution.parser import ResolutionMatch


def _make_event(**overrides) -> NormalizedNewsEvent:
    defaults = dict(
        event_id="evt-1",
        received_at=datetime.now(timezone.utc),
        source_name="Reuters",
        source_tier=SourceTier.TIER_2_TRUSTED_MEDIA,
        source_reliability_score=0.8,
        headline="Fed approves rate cut for March",
        topic_hints=["fed", "interest_rates"],
        novelty_hint=0.7,
    )
    defaults.update(overrides)
    return NormalizedNewsEvent(**defaults)


def _make_market(**overrides) -> MarketCandidate:
    defaults = dict(
        market_id="mkt-1",
        condition_id="cond-1",
        market_title="Will the Fed cut rates in March?",
        resolution_text="Resolves YES if the Federal Reserve cuts rates by March 31.",
        liquidity_score=0.8,
        mapping_confidence=0.7,
    )
    defaults.update(overrides)
    return MarketCandidate(**defaults)


def _make_resolution_match(**overrides) -> ResolutionMatch:
    defaults = dict(
        event_id="evt-1",
        market_id="mkt-1",
        match_score=0.6,
        matched_phrases=["cut rates"],
        reasoning="test",
        sufficient_for_trade=True,
    )
    defaults.update(overrides)
    return ResolutionMatch(**defaults)


class TestDirectionDetection:
    def test_positive_headline(self):
        assert _detect_direction("Fed approves new rate cut") == "positive"

    def test_negative_headline(self):
        assert _detect_direction("Congress rejects stimulus bill") == "negative"

    def test_neutral_headline(self):
        assert _detect_direction("Markets open for trading today") == "neutral"

    def test_mixed_leans_positive(self):
        assert _detect_direction("Bill approved and signed into law despite opposition") == "positive"


class TestCalculateShift:
    def test_positive_shift(self):
        shift = _calculate_shift("positive", 0.8, 0.7, 0.6)
        assert shift > 0

    def test_negative_shift(self):
        shift = _calculate_shift("negative", 0.8, 0.7, 0.6)
        assert shift < 0

    def test_neutral_no_shift(self):
        shift = _calculate_shift("neutral", 0.8, 0.7, 0.6)
        assert shift == 0.0

    def test_low_quality_reduces_shift(self):
        high = _calculate_shift("positive", 0.9, 0.8, 0.8)
        low = _calculate_shift("positive", 0.2, 0.8, 0.8)
        assert high > low


class TestProbabilityEngine:
    def test_basic_assessment(self):
        engine = ProbabilityEngine({"probability": {"method": "rule_based"}})
        event = _make_event()
        market = _make_market()
        res_match = _make_resolution_match()

        result = engine.assess(event, market, res_match, 0.5)
        assert 0.0 < result.model_probability <= 1.0
        assert 0.0 < result.confidence_score <= 1.0
        assert result.method == "rule_based"
        assert result.event_id == "evt-1"
        assert result.market_id == "mkt-1"

    def test_positive_news_increases_probability(self):
        engine = ProbabilityEngine({})
        event = _make_event(headline="Congress approves landmark bill")
        result = engine.assess(event, _make_market(), _make_resolution_match(), 0.5)
        assert result.model_probability > 0.5

    def test_negative_news_decreases_probability(self):
        engine = ProbabilityEngine({})
        event = _make_event(headline="Government rejects proposal entirely")
        result = engine.assess(event, _make_market(), _make_resolution_match(), 0.5)
        assert result.model_probability < 0.5

    def test_high_tier_source_higher_confidence(self):
        engine = ProbabilityEngine({})
        tier1 = _make_event(
            source_tier=SourceTier.TIER_1_PRIMARY,
            source_reliability_score=0.95,
        )
        tier4 = _make_event(
            source_tier=SourceTier.TIER_4_RUMOR,
            source_reliability_score=0.25,
        )
        res_match = _make_resolution_match()
        r1 = engine.assess(tier1, _make_market(), res_match, 0.5)
        r4 = engine.assess(tier4, _make_market(), res_match, 0.5)
        assert r1.confidence_score > r4.confidence_score

    def test_probability_clamped(self):
        engine = ProbabilityEngine({})
        event = _make_event(
            headline="Massive surge rally breaks all records approve confirm launch",
            source_reliability_score=1.0,
            novelty_hint=1.0,
        )
        res_match = _make_resolution_match(match_score=1.0)
        result = engine.assess(event, _make_market(), res_match, 0.95)
        assert result.model_probability <= 0.99
