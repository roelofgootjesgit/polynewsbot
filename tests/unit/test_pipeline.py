"""Tests for the pipeline orchestrator and decision logger."""
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.audit.decision_logger import DecisionLogger, DecisionTrace
from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.markets import MarketCandidate, MarketState
from src.pipeline.orchestrator import EventPipeline, PipelineStats


# ── Decision Logger Tests ────────────────────────────────────────────────


class TestDecisionTrace:
    def test_create_trace(self):
        trace = DecisionTrace("evt-1", "Fed cuts rates")
        assert trace.event_id == "evt-1"
        assert trace.outcome == "pending"

    def test_add_steps(self):
        trace = DecisionTrace("evt-1", "Fed cuts rates")
        trace.add_step("filter", {"score": 0.8})
        trace.add_step("mapping", {"candidates": 2})
        assert len(trace.steps) == 2
        assert trace.steps["filter"]["score"] == 0.8

    def test_set_outcome(self):
        trace = DecisionTrace("evt-1", "headline")
        trace.set_outcome("vetoed", "spread too wide")
        assert trace.outcome == "vetoed"
        assert trace.final_reason == "spread too wide"

    def test_to_dict(self):
        trace = DecisionTrace("evt-1", "headline")
        trace.add_step("edge", {"net_edge": 0.05})
        trace.set_outcome("executed", "YES @ 0.55")
        d = trace.to_dict()
        assert d["event_id"] == "evt-1"
        assert d["outcome"] == "executed"
        assert "edge" in d["steps"]


class TestDecisionLogger:
    def test_flush_writes_file(self, tmp_path):
        cfg = {"audit": {"log_decisions": True, "log_dir": str(tmp_path / "decisions")}}
        dl = DecisionLogger(cfg)
        trace = dl.create_trace("evt-1", "Test headline")
        trace.set_outcome("executed")
        count = dl.flush()
        assert count == 1
        files = list((tmp_path / "decisions").glob("*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event_id"] == "evt-1"

    def test_flush_disabled(self):
        cfg = {"audit": {"log_decisions": False}}
        dl = DecisionLogger(cfg)
        dl.create_trace("evt-1", "headline")
        assert dl.flush() == 0

    def test_pending_count(self):
        dl = DecisionLogger({})
        dl.create_trace("evt-1", "h1")
        dl.create_trace("evt-2", "h2")
        assert dl.pending_count == 2


# ── Pipeline Stats Tests ─────────────────────────────────────────────────


class TestPipelineStats:
    def test_summary_string(self):
        stats = PipelineStats()
        stats.events_polled = 5
        stats.events_passed_filter = 2
        stats.markets_matched = 3
        s = stats.summary()
        assert "polled=5" in s
        assert "filtered=2" in s
        assert "matched=3" in s


# ── Pipeline Orchestrator Tests ──────────────────────────────────────────


def _make_event(**overrides) -> NormalizedNewsEvent:
    defaults = dict(
        event_id="evt-test",
        received_at=datetime.now(timezone.utc),
        source_name="Reuters",
        source_tier=SourceTier.TIER_2_TRUSTED_MEDIA,
        source_reliability_score=0.8,
        headline="Fed approves rate cut for March 2025",
        topic_hints=["fed", "interest_rates", "economics"],
        novelty_hint=0.7,
    )
    defaults.update(overrides)
    return NormalizedNewsEvent(**defaults)


def _make_market(**overrides) -> MarketCandidate:
    defaults = dict(
        market_id="token-abc",
        condition_id="cond-abc",
        market_title="Will the Fed cut rates in March?",
        market_category="economics",
        resolution_text="Resolves YES if the Federal Reserve cuts rates by March 31.",
        liquidity_score=0.8,
        mapping_confidence=0.7,
        event_cluster_id="fed-rate-cut",
    )
    defaults.update(overrides)
    return MarketCandidate(**defaults)


class TestEventPipeline:
    def _default_cfg(self):
        return {
            "news": {"poll_interval_seconds": 1, "sources": {"rss": {"enabled": False}}},
            "filter": {"min_relevance_score": 0.3, "categories": ["economics"]},
            "mapping": {"min_mapping_confidence": 0.3, "min_liquidity_score": 0.1},
            "resolution": {"min_understanding_confidence": 0.3},
            "probability": {"method": "rule_based"},
            "edge": {"min_raw_edge": 0.03, "min_net_edge": 0.01, "fee_rate": 0.01,
                     "slippage_estimate": 0.005, "uncertainty_penalty_weight": 0.2},
            "risk": {"max_position_pct": 0.02, "max_cluster_pct": 0.05,
                     "max_total_exposure_pct": 0.20, "min_confidence": 0.3,
                     "max_spread": 0.10, "max_daily_loss_pct": 0.05,
                     "equity_kill_switch_pct": 0.15},
            "execution": {"dry_run": True},
            "polymarket": {},
            "audit": {"log_decisions": False},
        }

    def test_run_cycle_no_news(self):
        """Empty poll returns zero stats."""
        cfg = self._default_cfg()
        pipeline = EventPipeline(cfg)
        pipeline.poller = MagicMock()
        pipeline.poller.poll.return_value = []

        stats = pipeline.run_cycle()
        assert stats.events_polled == 0
        assert stats.trades_executed == 0

    def test_run_cycle_with_event_no_market_match(self):
        """Event passes filter but no market matches."""
        cfg = self._default_cfg()
        pipeline = EventPipeline(cfg)

        event = _make_event()
        pipeline.poller = MagicMock()
        pipeline.poller.poll.return_value = [event]

        stats = pipeline.run_cycle()
        assert stats.events_polled == 1
        assert stats.events_passed_filter == 1
        assert stats.markets_matched == 0

    @patch("src.pipeline.orchestrator.EventPipeline._get_market_state")
    def test_process_event_full_path(self, mock_state):
        """Event → mapping → edge → guardrail → dry-run execution."""
        cfg = self._default_cfg()
        pipeline = EventPipeline(cfg)
        pipeline._capital = 10_000

        market = _make_market()
        pipeline.universe._markets = [market]

        mock_state.return_value = MarketState(
            market_id="token-abc",
            timestamp=datetime.now(timezone.utc),
            best_bid=0.48,
            best_ask=0.52,
            spread=0.04,
            mid_price=0.50,
            implied_probability=0.50,
            estimated_slippage_bps=50,
            liquidity_quality="high",
        )

        event = _make_event()
        stats = PipelineStats()
        pipeline._process_event(event, stats)

        assert stats.markets_matched >= 1
        assert stats.edges_found >= 1
        # Trade may or may not be approved depending on edge thresholds
        assert (stats.trades_approved + stats.vetoed) >= 1

    @patch("src.pipeline.orchestrator.EventPipeline._get_market_state")
    def test_vetoed_on_low_liquidity(self, mock_state):
        """Low liquidity should trigger guardrail veto."""
        cfg = self._default_cfg()
        pipeline = EventPipeline(cfg)
        pipeline._capital = 10_000

        market = _make_market()
        pipeline.universe._markets = [market]

        mock_state.return_value = MarketState(
            market_id="token-abc",
            timestamp=datetime.now(timezone.utc),
            best_bid=0.48,
            best_ask=0.52,
            spread=0.04,
            mid_price=0.50,
            implied_probability=0.50,
            estimated_slippage_bps=50,
            liquidity_quality="low",
        )

        event = _make_event()
        stats = PipelineStats()
        pipeline._process_event(event, stats)

        assert stats.vetoed >= 1
