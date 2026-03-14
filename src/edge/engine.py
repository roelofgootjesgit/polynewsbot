"""
Edge engine — combines probability assessment + market state into a trade decision.
Only produces a trade signal when net edge survives all cost deductions.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from src.models.markets import MarketState
from src.models.probability import ProbabilityAssessment
from src.models.trades import TradeDecision

logger = logging.getLogger(__name__)


class EdgeEngine:
    """Calculates raw and net edge, decides if a trade is worth taking."""

    def __init__(self, cfg: dict[str, Any]):
        edge_cfg = cfg.get("edge", {})
        self.min_raw_edge: float = edge_cfg.get("min_raw_edge", 0.05)
        self.min_net_edge: float = edge_cfg.get("min_net_edge", 0.03)
        self.fee_rate: float = edge_cfg.get("fee_rate", 0.02)
        self.slippage_est: float = edge_cfg.get("slippage_estimate", 0.01)
        self.uncertainty_weight: float = edge_cfg.get("uncertainty_penalty_weight", 0.5)

    def evaluate(
        self,
        assessment: ProbabilityAssessment,
        market_state: MarketState,
    ) -> TradeDecision:
        """Evaluate if there is actionable edge."""
        market_prob = market_state.implied_probability or 0.5
        model_prob = assessment.model_probability

        if model_prob > market_prob:
            side = "YES"
            raw_edge = model_prob - market_prob
        else:
            side = "NO"
            raw_edge = market_prob - model_prob

        slippage = (market_state.estimated_slippage_bps or 0) / 10_000
        actual_slippage = max(slippage, self.slippage_est)

        uncertainty_penalty = (1.0 - assessment.confidence_score) * self.uncertainty_weight * raw_edge

        net_edge = raw_edge - self.fee_rate - actual_slippage - uncertainty_penalty

        raw_ok = raw_edge >= self.min_raw_edge
        net_ok = net_edge >= self.min_net_edge
        execution_allowed = raw_ok and net_ok

        reasons = []
        if not raw_ok:
            reasons.append(f"raw_edge {raw_edge:.4f} < {self.min_raw_edge}")
        if not net_ok:
            reasons.append(f"net_edge {net_edge:.4f} < {self.min_net_edge}")

        decision_reason = (
            f"Side: {side}. "
            f"Model: {model_prob:.4f}, Market: {market_prob:.4f}. "
            f"Raw edge: {raw_edge:.4f}, Net edge: {net_edge:.4f}. "
            f"Fees: {self.fee_rate}, Slippage: {actual_slippage:.4f}, "
            f"Uncertainty penalty: {uncertainty_penalty:.4f}."
        )

        return TradeDecision(
            event_id=assessment.event_id,
            market_id=assessment.market_id,
            timestamp=datetime.now(timezone.utc),
            side=side,
            raw_edge=round(raw_edge, 4),
            net_edge=round(net_edge, 4),
            model_probability=model_prob,
            market_probability=market_prob,
            execution_allowed=execution_allowed,
            guardrail_status="pending",
            veto_reasons=reasons,
            decision_reason=decision_reason,
            confidence=assessment.confidence_score,
            source_quality=assessment.source_quality_score,
        )
