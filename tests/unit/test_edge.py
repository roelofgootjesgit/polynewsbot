"""Tests for the edge engine."""
from datetime import datetime, timezone

from src.edge.engine import EdgeEngine
from src.models.markets import MarketState
from src.models.probability import ProbabilityAssessment


def _make_assessment(**overrides) -> ProbabilityAssessment:
    defaults = dict(
        event_id="evt-1",
        market_id="mkt-1",
        model_probability=0.70,
        confidence_score=0.8,
        source_quality_score=0.8,
        novelty_score=0.7,
        resolution_match_score=0.6,
        already_priced_risk=0.1,
        reasoning_summary="test",
        method="rule_based",
        claim_direction="positive",
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


class TestEdgeEngine:
    def test_yes_side_when_model_higher(self):
        engine = EdgeEngine({"edge": {"min_raw_edge": 0.05, "min_net_edge": 0.01}})
        result = engine.evaluate(
            _make_assessment(model_probability=0.70),
            _make_market_state(implied_probability=0.50),
        )
        assert result.side == "YES"
        assert result.raw_edge == 0.20

    def test_no_side_when_model_lower(self):
        engine = EdgeEngine({"edge": {"min_raw_edge": 0.05, "min_net_edge": 0.01}})
        result = engine.evaluate(
            _make_assessment(model_probability=0.30),
            _make_market_state(implied_probability=0.50),
        )
        assert result.side == "NO"
        assert result.raw_edge == 0.20

    def test_edge_calculation(self):
        engine = EdgeEngine({
            "edge": {
                "min_raw_edge": 0.05,
                "min_net_edge": 0.01,
                "fee_rate": 0.02,
                "slippage_estimate": 0.01,
                "uncertainty_penalty_weight": 0.5,
            }
        })
        assessment = _make_assessment(model_probability=0.70, confidence_score=0.8)
        state = _make_market_state(implied_probability=0.50, estimated_slippage_bps=50)

        result = engine.evaluate(assessment, state)

        assert result.raw_edge == 0.20
        slippage = max(50 / 10000, 0.01)
        uncertainty = (1.0 - 0.8) * 0.5 * 0.20
        expected_net = 0.20 - 0.02 - slippage - uncertainty
        assert abs(result.net_edge - round(expected_net, 4)) < 0.001

    def test_execution_blocked_on_low_edge(self):
        engine = EdgeEngine({"edge": {"min_raw_edge": 0.10, "min_net_edge": 0.05}})
        result = engine.evaluate(
            _make_assessment(model_probability=0.53),
            _make_market_state(implied_probability=0.50),
        )
        assert result.execution_allowed is False
        assert len(result.veto_reasons) > 0

    def test_execution_allowed_on_high_edge(self):
        engine = EdgeEngine({
            "edge": {
                "min_raw_edge": 0.05,
                "min_net_edge": 0.01,
                "fee_rate": 0.01,
                "slippage_estimate": 0.005,
                "uncertainty_penalty_weight": 0.2,
            }
        })
        result = engine.evaluate(
            _make_assessment(model_probability=0.80, confidence_score=0.9),
            _make_market_state(implied_probability=0.50),
        )
        assert result.execution_allowed is True
        assert result.raw_edge >= 0.05
        assert result.net_edge >= 0.01
