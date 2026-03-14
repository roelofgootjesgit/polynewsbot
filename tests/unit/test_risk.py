"""Tests for risk management: sizing, exposure, and guardrails."""
from datetime import datetime, timezone

from src.models.events import SourceTier
from src.models.markets import MarketState
from src.models.probability import ProbabilityAssessment
from src.models.trades import TradeDecision, Position
from src.risk.sizing import PositionSizer
from src.risk.exposure import ExposureTracker
from src.risk.guardrails import Guardrails


def _make_decision(**overrides) -> TradeDecision:
    defaults = dict(
        event_id="evt-1",
        market_id="mkt-1",
        timestamp=datetime.now(timezone.utc),
        side="YES",
        raw_edge=0.15,
        net_edge=0.08,
        model_probability=0.65,
        market_probability=0.50,
        execution_allowed=True,
        guardrail_status="pending",
        veto_reasons=[],
        decision_reason="test",
        confidence=0.75,
        source_quality=0.8,
    )
    defaults.update(overrides)
    return TradeDecision(**defaults)


def _make_assessment(**overrides) -> ProbabilityAssessment:
    defaults = dict(
        event_id="evt-1",
        market_id="mkt-1",
        model_probability=0.65,
        confidence_score=0.75,
        source_quality_score=0.8,
        novelty_score=0.7,
        resolution_match_score=0.6,
        already_priced_risk=0.1,
        reasoning_summary="test",
    )
    defaults.update(overrides)
    return ProbabilityAssessment(**defaults)


def _make_market_state(**overrides) -> MarketState:
    defaults = dict(
        market_id="mkt-1",
        timestamp=datetime.now(timezone.utc),
        best_bid=0.48,
        best_ask=0.52,
        spread=0.04,
        mid_price=0.50,
        implied_probability=0.50,
        estimated_slippage_bps=50,
        liquidity_quality="high",
    )
    defaults.update(overrides)
    return MarketState(**defaults)


def _make_position(pos_id: str, cost_basis: float = 100.0, status: str = "open") -> Position:
    return Position(
        position_id=pos_id,
        market_id="mkt-1",
        event_id="evt-1",
        side="YES",
        entry_price=0.50,
        entry_timestamp=datetime.now(timezone.utc),
        shares=200.0,
        cost_basis_usd=cost_basis,
        original_model_probability=0.65,
        original_confidence=0.75,
        status=status,
    )


# --- Position Sizer ---

class TestPositionSizer:
    def test_basic_sizing(self):
        sizer = PositionSizer({"risk": {"max_position_pct": 0.02}})
        size = sizer.calculate(capital=10000, price=0.50, confidence=0.8)
        assert size > 0
        assert size <= 10000 * 0.02

    def test_zero_capital(self):
        sizer = PositionSizer({"risk": {}})
        assert sizer.calculate(capital=0, price=0.50, confidence=0.8) == 0.0

    def test_confidence_scales_size(self):
        sizer = PositionSizer({"risk": {"max_position_pct": 0.02}})
        high = sizer.calculate(capital=10000, price=0.50, confidence=1.0)
        low = sizer.calculate(capital=10000, price=0.50, confidence=0.2)
        assert high > low

    def test_cluster_limit(self):
        sizer = PositionSizer({"risk": {"max_position_pct": 0.10, "max_cluster_pct": 0.05}})
        size = sizer.calculate(
            capital=10000, price=0.50, confidence=0.8,
            cluster_exposure=400.0,
        )
        assert size <= (10000 * 0.05 - 400.0) * 1.0

    def test_total_exposure_limit(self):
        sizer = PositionSizer({
            "risk": {
                "max_position_pct": 0.10,
                "max_cluster_pct": 0.50,
                "max_total_exposure_pct": 0.05,
            }
        })
        size = sizer.calculate(
            capital=10000, price=0.50, confidence=0.8,
            total_exposure=400.0,
        )
        assert size <= (10000 * 0.05 - 400.0) * 1.0


# --- Exposure Tracker ---

class TestExposureTracker:
    def test_add_and_total(self):
        tracker = ExposureTracker()
        tracker.add_position(_make_position("p1", 100))
        tracker.add_position(_make_position("p2", 200))
        assert tracker.get_total_exposure() == 300.0

    def test_remove_position(self):
        tracker = ExposureTracker()
        tracker.add_position(_make_position("p1", 100))
        tracker.remove_position("p1")
        assert tracker.get_total_exposure() == 0.0

    def test_closed_not_counted(self):
        tracker = ExposureTracker()
        tracker.add_position(_make_position("p1", 100, status="closed"))
        assert tracker.get_total_exposure() == 0.0

    def test_position_count(self):
        tracker = ExposureTracker()
        tracker.add_position(_make_position("p1"))
        tracker.add_position(_make_position("p2"))
        tracker.add_position(_make_position("p3", status="closed"))
        assert tracker.get_position_count() == 2


# --- Guardrails ---

class TestGuardrails:
    def _default_cfg(self):
        return {
            "risk": {
                "max_position_pct": 0.02,
                "max_cluster_pct": 0.05,
                "max_total_exposure_pct": 0.20,
                "min_source_tier": 3,
                "min_confidence": 0.5,
                "max_spread": 0.10,
                "max_daily_loss_pct": 0.05,
                "equity_kill_switch_pct": 0.15,
            }
        }

    def test_approved_trade(self):
        g = Guardrails(self._default_cfg())
        result = g.evaluate(
            _make_decision(),
            _make_assessment(),
            _make_market_state(),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is True
        assert result.position_size_usd > 0

    def test_veto_low_confidence(self):
        g = Guardrails(self._default_cfg())
        result = g.evaluate(
            _make_decision(confidence=0.2),
            _make_assessment(confidence_score=0.2),
            _make_market_state(),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is False
        assert any("confidence" in r for r in result.veto_reasons)

    def test_veto_wide_spread(self):
        g = Guardrails(self._default_cfg())
        result = g.evaluate(
            _make_decision(),
            _make_assessment(),
            _make_market_state(spread=0.15),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is False
        assert any("spread" in r for r in result.veto_reasons)

    def test_veto_low_liquidity(self):
        g = Guardrails(self._default_cfg())
        result = g.evaluate(
            _make_decision(),
            _make_assessment(),
            _make_market_state(liquidity_quality="low"),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is False

    def test_veto_weak_resolution_match(self):
        g = Guardrails(self._default_cfg())
        result = g.evaluate(
            _make_decision(),
            _make_assessment(resolution_match_score=0.1),
            _make_market_state(),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is False

    def test_veto_execution_not_allowed(self):
        g = Guardrails(self._default_cfg())
        result = g.evaluate(
            _make_decision(execution_allowed=False, veto_reasons=["edge too low"]),
            _make_assessment(),
            _make_market_state(),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is False

    def test_kill_switch(self):
        g = Guardrails(self._default_cfg())
        g.check_kill_switch(capital=10000, initial_capital=10000)
        triggered = g.check_kill_switch(capital=8500, initial_capital=10000)
        assert triggered is True
        result = g.evaluate(
            _make_decision(),
            _make_assessment(),
            _make_market_state(),
            ExposureTracker(),
            capital=8500,
        )
        assert result.approved is False
        assert any("kill switch" in r for r in result.veto_reasons)

    def test_daily_loss_limit(self):
        g = Guardrails(self._default_cfg())
        g.update_daily_pnl(-600)
        result = g.evaluate(
            _make_decision(),
            _make_assessment(),
            _make_market_state(),
            ExposureTracker(),
            capital=10000,
        )
        assert result.approved is False
        assert any("daily loss" in r for r in result.veto_reasons)
