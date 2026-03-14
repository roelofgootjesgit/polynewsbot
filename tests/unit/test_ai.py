"""Tests for the AI/LLM layer — client, prompts, hybrid engines."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.ai.hybrid import HybridProbabilityEngine, HybridResolutionParser
from src.ai.llm_client import LLMClient, LLMCostTracker, LLMUsage, _estimate_cost
from src.ai.llm_probability import LLMProbabilityEngine
from src.ai.llm_resolution import LLMResolutionParser
from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.markets import MarketCandidate
from src.resolution.parser import ResolutionCriteria, ResolutionMatch


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


# --- Cost Tracker ---

class TestLLMCostTracker:
    def test_empty_tracker(self):
        tracker = LLMCostTracker()
        assert tracker.total_calls == 0
        assert tracker.total_tokens == 0
        assert tracker.total_cost_usd == 0.0

    def test_record_usage(self):
        tracker = LLMCostTracker()
        tracker.record(LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150,
                                estimated_cost_usd=0.001, model="gpt-4o-mini"))
        tracker.record(LLMUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300,
                                estimated_cost_usd=0.002, model="gpt-4o-mini"))
        assert tracker.total_calls == 2
        assert tracker.total_tokens == 450
        assert abs(tracker.total_cost_usd - 0.003) < 0.0001

    def test_summary_string(self):
        tracker = LLMCostTracker()
        tracker.record(LLMUsage(total_tokens=100, estimated_cost_usd=0.001))
        s = tracker.summary()
        assert "1 calls" in s
        assert "100 tokens" in s


class TestCostEstimation:
    def test_gpt4o_mini_cost(self):
        cost = _estimate_cost("gpt-4o-mini", 1000, 500)
        assert cost > 0
        assert cost < 0.01

    def test_unknown_model_uses_default(self):
        cost = _estimate_cost("unknown-model", 1000, 500)
        assert cost > 0


# --- LLM Client ---

class TestLLMClient:
    def test_no_key_not_available(self):
        client = LLMClient({"ai": {"openai_api_key": ""}})
        ok = client.connect()
        assert ok is False
        assert client.available is False

    def test_chat_raises_when_unavailable(self):
        client = LLMClient({})
        import pytest
        with pytest.raises(RuntimeError):
            client.chat("system", "user")


# --- LLM Probability Engine (mocked) ---

class TestLLMProbabilityEngine:
    def test_assess_with_mock_llm(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.available = True
        mock_llm.chat_json.return_value = (
            {
                "probability": 0.72,
                "confidence": 0.8,
                "direction": "positive",
                "reasoning": "Rate cut confirmed by Fed.",
                "already_priced_risk": 0.3,
            },
            LLMUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280,
                     estimated_cost_usd=0.001, model="gpt-4o-mini", latency_ms=500),
        )

        engine = LLMProbabilityEngine(mock_llm)
        result = engine.assess(_make_event(), _make_market(), _make_resolution_match(), 0.5)

        assert result.model_probability == 0.72
        assert result.confidence_score == 0.8
        assert result.claim_direction == "positive"
        assert result.method == "llm"
        assert "[LLM]" in result.reasoning_summary


# --- LLM Resolution Parser (mocked) ---

class TestLLMResolutionParser:
    def test_parse_criteria_with_mock(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.available = True
        mock_llm.chat_json.return_value = (
            {
                "resolution_type": "binary",
                "key_conditions": ["Federal Reserve cuts rates", "Before March 31"],
                "requires_official_source": True,
                "has_deadline": True,
                "deadline_description": "March 31, 2026",
                "ambiguity_level": "low",
                "confidence": 0.9,
            },
            LLMUsage(total_tokens=200, estimated_cost_usd=0.001),
        )

        parser = LLMResolutionParser(mock_llm)
        criteria = parser.parse_criteria(_make_market())

        assert criteria.resolution_type == "binary"
        assert len(criteria.key_phrases) == 2
        assert criteria.requires_official_source is True
        assert criteria.confidence == 0.9

    def test_match_event_with_mock(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.available = True
        mock_llm.chat_json.return_value = (
            {
                "match_score": 0.85,
                "matched_conditions": ["Federal Reserve cuts rates"],
                "reasoning": "Direct confirmation of rate cut.",
                "sufficient_for_resolution": True,
            },
            LLMUsage(total_tokens=180, estimated_cost_usd=0.001),
        )

        parser = LLMResolutionParser(mock_llm)
        criteria = ResolutionCriteria(
            market_id="mkt-1",
            resolution_text="Resolves YES if Fed cuts rates.",
            key_phrases=["Federal Reserve cuts rates"],
            resolution_type="binary",
        )
        match = parser.match_event(_make_event(), criteria)

        assert match.match_score == 0.85
        assert match.sufficient_for_trade is True
        assert "[LLM]" in match.reasoning


# --- Hybrid Engine ---

class TestHybridProbabilityEngine:
    def test_rule_based_mode(self):
        engine = HybridProbabilityEngine({"probability": {"method": "rule_based"}})
        result = engine.assess(_make_event(), _make_market(), _make_resolution_match(), 0.5)
        assert result.method == "rule_based"
        assert not engine.llm_available

    def test_hybrid_fallback_on_no_llm(self):
        engine = HybridProbabilityEngine({"probability": {"method": "hybrid"}})
        result = engine.assess(_make_event(), _make_market(), _make_resolution_match(), 0.5)
        assert result.model_probability > 0
        assert "[LLM]" not in result.reasoning_summary

    def test_hybrid_uses_llm_when_available(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.available = True
        mock_llm.chat_json.return_value = (
            {"probability": 0.65, "confidence": 0.7, "direction": "positive",
             "reasoning": "LLM says yes", "already_priced_risk": 0.2},
            LLMUsage(total_tokens=200, estimated_cost_usd=0.001),
        )

        engine = HybridProbabilityEngine({"probability": {"method": "hybrid"}}, mock_llm)
        result = engine.assess(_make_event(), _make_market(), _make_resolution_match(), 0.5)
        assert result.method == "llm"
        assert engine.llm_available

    def test_hybrid_falls_back_on_llm_error(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.available = True
        mock_llm.chat_json.side_effect = RuntimeError("API timeout")

        engine = HybridProbabilityEngine({"probability": {"method": "hybrid"}}, mock_llm)
        result = engine.assess(_make_event(), _make_market(), _make_resolution_match(), 0.5)
        assert result.model_probability > 0
        assert "[LLM]" not in result.reasoning_summary


class TestHybridResolutionParser:
    def test_rule_based_mode(self):
        parser = HybridResolutionParser({"probability": {"method": "rule_based"}})
        criteria = parser.parse_criteria(_make_market())
        assert criteria.market_id == "mkt-1"

    def test_hybrid_fallback_on_error(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.available = True
        mock_llm.chat_json.side_effect = ValueError("bad json")

        parser = HybridResolutionParser({"probability": {"method": "hybrid"}}, mock_llm)
        criteria = parser.parse_criteria(_make_market())
        assert criteria.market_id == "mkt-1"
