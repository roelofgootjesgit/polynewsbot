"""Tests for Pydantic data models."""
import uuid
from datetime import datetime

from src.models.events import NormalizedNewsEvent, SourceTier, RawNewsItem
from src.models.markets import MarketCandidate, MarketState
from src.models.probability import ProbabilityAssessment
from src.models.trades import TradeDecision, Position


def test_normalized_news_event():
    event = NormalizedNewsEvent(
        event_id=str(uuid.uuid4()),
        received_at=datetime.now(),
        source_name="Reuters",
        source_tier=SourceTier.TIER_2_TRUSTED_MEDIA,
        source_reliability_score=0.85,
        headline="Fed raises interest rates by 25bps",
        topic_hints=["fed", "interest_rates"],
    )
    assert event.source_tier == 2
    assert event.source_reliability_score == 0.85
    assert not event.is_duplicate


def test_source_tier_ordering():
    assert SourceTier.TIER_1_PRIMARY < SourceTier.TIER_4_RUMOR
    assert SourceTier.TIER_2_TRUSTED_MEDIA < SourceTier.TIER_3_SECONDARY


def test_market_candidate():
    mc = MarketCandidate(
        market_id="0x123",
        condition_id="0xabc",
        market_title="Will the Fed raise rates in March 2026?",
        resolution_text="Resolves YES if the Federal Reserve raises the target rate.",
        mapping_confidence=0.8,
    )
    assert mc.active is True
    assert mc.mapping_confidence == 0.8


def test_market_state():
    ms = MarketState(
        market_id="0x123",
        timestamp=datetime.now(),
        best_bid=0.55,
        best_ask=0.58,
        spread=0.03,
        mid_price=0.565,
        implied_probability=0.565,
    )
    assert ms.spread == 0.03


def test_probability_assessment():
    pa = ProbabilityAssessment(
        event_id="evt-1",
        market_id="0x123",
        model_probability=0.72,
        confidence_score=0.8,
        source_quality_score=0.85,
        novelty_score=0.9,
        resolution_match_score=0.75,
        reasoning_summary="Official Fed statement confirms rate hike, high confidence.",
    )
    assert pa.model_probability == 0.72
    assert pa.method == "rule_based"


def test_trade_decision():
    td = TradeDecision(
        event_id="evt-1",
        market_id="0x123",
        timestamp=datetime.now(),
        side="YES",
        raw_edge=0.10,
        net_edge=0.06,
        model_probability=0.72,
        market_probability=0.62,
        execution_allowed=True,
        guardrail_status="passed",
        decision_reason="Net edge above threshold, all guardrails passed.",
        confidence=0.8,
    )
    assert td.execution_allowed
    assert td.net_edge > 0


def test_position():
    pos = Position(
        position_id="pos-1",
        market_id="0x123",
        event_id="evt-1",
        side="YES",
        entry_price=0.62,
        entry_timestamp=datetime.now(),
        shares=100.0,
        cost_basis_usd=62.0,
        original_model_probability=0.72,
        original_confidence=0.8,
    )
    assert pos.status == "pending"
    assert pos.thesis_still_valid is True
