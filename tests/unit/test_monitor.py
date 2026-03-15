"""Tests for position monitor, exit engine, and counter-news detection."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.trades import Position
from src.monitor.counter_news import CounterNewsDetector, _get_direction
from src.monitor.exit_engine import ExitEngine, ExitResult
from src.monitor.position_monitor import (
    MonitorConfig, PositionMonitor, PositionSnapshot, ThesisState,
)
from src.risk.exposure import ExposureTracker


def _make_position(**overrides) -> Position:
    defaults = dict(
        position_id="pos-1",
        market_id="mkt-bitcoin-up",
        event_id="evt-bitcoin",
        side="YES",
        entry_price=0.55,
        entry_timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
        shares=100.0,
        cost_basis_usd=55.0,
        original_model_probability=0.65,
        original_confidence=0.7,
        status="open",
    )
    defaults.update(overrides)
    return Position(**defaults)


def _make_event(**overrides) -> NormalizedNewsEvent:
    defaults = dict(
        event_id="evt-new",
        received_at=datetime.now(timezone.utc),
        source_name="Reuters",
        source_tier=SourceTier.TIER_2_TRUSTED_MEDIA,
        source_reliability_score=0.8,
        headline="Bitcoin drops sharply amid market sell-off",
        topic_hints=["bitcoin", "crypto"],
    )
    defaults.update(overrides)
    return NormalizedNewsEvent(**defaults)


# --- Position Monitor ---

class TestPositionMonitor:
    def test_register_and_check_no_exit(self):
        monitor = PositionMonitor({"monitor": {}})
        pos = _make_position()
        monitor.register_position(pos, 0.65, 0.05)

        snap = monitor.check_position(pos, 0.56)
        assert snap.exit_signal is None
        assert snap.thesis_state == ThesisState.VALID
        assert snap.unrealized_pnl_usd > 0

    def test_repricing_complete_triggers_exit(self):
        monitor = PositionMonitor({"monitor": {"take_profit_edge_absorbed": 0.70}})
        pos = _make_position(entry_price=0.55)
        monitor.register_position(pos, 0.65, 0.05)

        snap = monitor.check_position(pos, 0.63)
        assert snap.repricing_pct >= 0.70
        assert snap.exit_signal == "exit_repricing_complete"

    def test_time_limit_triggers_exit(self):
        monitor = PositionMonitor({"monitor": {"time_exit_hours": 2.0}})
        pos = _make_position(
            entry_timestamp=datetime.now(timezone.utc) - timedelta(hours=3)
        )
        monitor.register_position(pos, 0.65, 0.05)

        snap = monitor.check_position(pos, 0.56)
        assert snap.exit_signal == "exit_time_limit"

    def test_thesis_invalidated_triggers_exit(self):
        monitor = PositionMonitor({"monitor": {"force_exit_thesis_invalid": True}})
        pos = _make_position()
        monitor.register_position(pos, 0.65, 0.05)

        monitor.invalidate_thesis(pos.position_id, "counter news")
        snap = monitor.check_position(pos, 0.56)
        assert snap.exit_signal == "exit_thesis_invalid"
        assert snap.thesis_state == ThesisState.INVALIDATED

    def test_thesis_weakened_no_exit(self):
        monitor = PositionMonitor({"monitor": {}})
        pos = _make_position()
        monitor.register_position(pos, 0.65, 0.05)

        monitor.weaken_thesis(pos.position_id, "conflicting signal")
        snap = monitor.check_position(pos, 0.56)
        assert snap.thesis_state == ThesisState.WEAKENED
        assert snap.exit_signal is None

    def test_pnl_calculation_yes_side(self):
        monitor = PositionMonitor({"monitor": {}})
        pos = _make_position(side="YES", entry_price=0.50, shares=100, cost_basis_usd=50)
        monitor.register_position(pos, 0.60, 0.05)

        snap = monitor.check_position(pos, 0.60)
        assert snap.unrealized_pnl_usd == 10.0

    def test_pnl_calculation_no_side(self):
        monitor = PositionMonitor({"monitor": {}})
        pos = _make_position(side="NO", entry_price=0.50, shares=100, cost_basis_usd=50)
        monitor.register_position(pos, 0.40, 0.05)

        snap = monitor.check_position(pos, 0.40)
        assert snap.unrealized_pnl_usd == 10.0

    def test_remove_position(self):
        monitor = PositionMonitor({"monitor": {}})
        pos = _make_position()
        monitor.register_position(pos, 0.65, 0.05)
        monitor.remove_position(pos.position_id)
        assert monitor.get_thesis_state(pos.position_id) == ThesisState.VALID


# --- Exit Engine ---

class TestExitEngine:
    def test_exit_on_signal(self):
        engine = ExitEngine({"execution": {"dry_run": True}})
        pos = _make_position()
        snap = PositionSnapshot(
            position_id=pos.position_id,
            market_id=pos.market_id,
            timestamp=datetime.now(timezone.utc),
            current_price=0.60,
            entry_price=0.55,
            side="YES",
            exit_signal="exit_repricing_complete",
            exit_reason="repricing 75% >= 70%",
        )

        from src.execution.order_manager import OrderManager
        om = OrderManager({"execution": {"dry_run": True}})
        exposure = ExposureTracker()
        exposure.add_position(pos)

        results = engine.process_exits(
            [snap], {pos.position_id: pos}, om, exposure
        )
        assert len(results) == 1
        assert results[0].executed is True
        assert pos.status == "closed"

    def test_no_exit_without_signal(self):
        engine = ExitEngine({"execution": {"dry_run": True}})
        snap = PositionSnapshot(
            position_id="pos-1",
            market_id="mkt-1",
            timestamp=datetime.now(timezone.utc),
            current_price=0.56,
            entry_price=0.55,
            side="YES",
        )

        from src.execution.order_manager import OrderManager
        om = OrderManager({"execution": {"dry_run": True}})
        results = engine.process_exits(
            [snap], {"pos-1": _make_position()}, om, ExposureTracker()
        )
        assert len(results) == 0


# --- Counter News ---

class TestCounterNews:
    def test_detect_contradiction(self):
        detector = CounterNewsDetector({"risk": {"min_source_tier": 3}})
        pos = _make_position(side="YES", market_id="bitcoin-up-market", event_id="evt-bitcoin")
        event = _make_event(
            headline="Bitcoin crashes below support level",
            topic_hints=["bitcoin"],
        )

        monitor = PositionMonitor({"monitor": {}})
        monitor.register_position(pos, 0.65, 0.05)

        affected = detector.check_against_positions(event, [pos], monitor)
        assert pos.position_id in affected
        assert monitor.get_thesis_state(pos.position_id) == ThesisState.INVALIDATED

    def test_no_contradiction_same_direction(self):
        detector = CounterNewsDetector({"risk": {"min_source_tier": 3}})
        pos = _make_position(side="YES", market_id="bitcoin-up-market", event_id="evt-bitcoin")
        event = _make_event(
            headline="Bitcoin surges to new all-time high",
            topic_hints=["bitcoin"],
        )

        monitor = PositionMonitor({"monitor": {}})
        monitor.register_position(pos, 0.65, 0.05)

        affected = detector.check_against_positions(event, [pos], monitor)
        assert len(affected) == 0

    def test_weak_source_weakens_only(self):
        detector = CounterNewsDetector({"risk": {"min_source_tier": 3}})
        pos = _make_position(side="YES", market_id="bitcoin-up-market", event_id="evt-bitcoin")
        event = _make_event(
            headline="Bitcoin drops amid selling pressure",
            topic_hints=["bitcoin"],
            source_tier=SourceTier.TIER_4_RUMOR,
            source_reliability_score=0.25,
        )

        monitor = PositionMonitor({"monitor": {}})
        monitor.register_position(pos, 0.65, 0.05)

        affected = detector.check_against_positions(event, [pos], monitor)
        assert pos.position_id in affected
        assert monitor.get_thesis_state(pos.position_id) == ThesisState.WEAKENED

    def test_direction_detection(self):
        assert _get_direction("prices surge higher") == "positive"
        assert _get_direction("market crashes hard") == "negative"
        assert _get_direction("weather is nice today") == "neutral"


# --- Edge Banding ---

class TestEdgeBanding:
    def _make_state(self, **kw):
        from src.models.markets import MarketState
        defaults = dict(market_id="m1", timestamp=datetime.now(timezone.utc))
        defaults.update(kw)
        return MarketState(**defaults)

    def test_strong_band(self):
        from src.edge.engine import EdgeEngine
        engine = EdgeEngine({"edge": {}})
        from src.models.probability import ProbabilityAssessment

        assessment = ProbabilityAssessment(
            event_id="e1", market_id="m1",
            model_probability=0.70, confidence_score=0.9,
            source_quality_score=0.8, novelty_score=0.8,
            resolution_match_score=0.7, already_priced_risk=0.1,
            reasoning_summary="test", method="rule_based",
            claim_direction="positive",
        )
        state = self._make_state(
            implied_probability=0.55,
            best_bid=0.54, best_ask=0.56, spread=0.02, mid_price=0.55,
        )

        decision = engine.evaluate(assessment, state)
        assert decision.edge_band == "strong"
        assert decision.execution_allowed is True
        assert decision.size_scale == 1.0

    def test_observe_band_not_executable(self):
        from src.edge.engine import EdgeEngine
        engine = EdgeEngine({"edge": {}})
        from src.models.probability import ProbabilityAssessment

        assessment = ProbabilityAssessment(
            event_id="e1", market_id="m1",
            model_probability=0.54, confidence_score=0.9,
            source_quality_score=0.8, novelty_score=0.8,
            resolution_match_score=0.7, already_priced_risk=0.1,
            reasoning_summary="test", method="rule_based",
            claim_direction="positive",
        )
        state = self._make_state(
            implied_probability=0.50,
            best_bid=0.49, best_ask=0.51, spread=0.02, mid_price=0.50,
        )

        decision = engine.evaluate(assessment, state)
        assert decision.edge_band == "observe"
        assert decision.execution_allowed is False

    def test_below_all_bands(self):
        from src.edge.engine import EdgeEngine
        engine = EdgeEngine({"edge": {}})
        from src.models.probability import ProbabilityAssessment

        assessment = ProbabilityAssessment(
            event_id="e1", market_id="m1",
            model_probability=0.51, confidence_score=0.5,
            source_quality_score=0.5, novelty_score=0.5,
            resolution_match_score=0.5, already_priced_risk=0.5,
            reasoning_summary="test", method="rule_based",
            claim_direction="neutral",
        )
        state = self._make_state(
            implied_probability=0.50,
            best_bid=0.49, best_ask=0.51, spread=0.02, mid_price=0.50,
        )

        decision = engine.evaluate(assessment, state)
        assert decision.edge_band == "below_threshold"
        assert decision.execution_allowed is False


# --- Guardrail Event Cooldown ---

class TestGuardrailCooldown:
    def test_cooldown_blocks_re_entry(self):
        from src.risk.guardrails import Guardrails, GuardrailResult
        from src.models.trades import TradeDecision
        from src.models.probability import ProbabilityAssessment
        from src.models.markets import MarketState

        g = Guardrails({"risk": {"event_cooldown_minutes": 30}})
        exposure = ExposureTracker()

        decision = TradeDecision(
            event_id="evt-1", market_id="mkt-1",
            timestamp=datetime.now(timezone.utc),
            side="YES", raw_edge=0.10, net_edge=0.06,
            model_probability=0.65, market_probability=0.55,
            execution_allowed=True, edge_band="strong", size_scale=1.0,
            confidence=0.8, source_quality=0.8,
        )
        assessment = ProbabilityAssessment(
            event_id="evt-1", market_id="mkt-1",
            model_probability=0.65, confidence_score=0.8,
            source_quality_score=0.8, novelty_score=0.7,
            resolution_match_score=0.6, already_priced_risk=0.1,
            reasoning_summary="test", method="rule_based",
            claim_direction="positive",
        )
        state = MarketState(
            market_id="mkt-1", timestamp=datetime.now(timezone.utc),
            implied_probability=0.55,
            best_bid=0.54, best_ask=0.56, spread=0.02,
            mid_price=0.55, liquidity_quality="medium",
        )

        r1 = g.evaluate(decision, assessment, state, exposure, 10000)
        assert r1.approved is True

        r2 = g.evaluate(decision, assessment, state, exposure, 10000)
        assert r2.approved is False
        assert any("cooldown" in r for r in r2.veto_reasons)
