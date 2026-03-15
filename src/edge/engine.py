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


class EdgeBand:
    """Represents one edge regime (strong/normal/observe)."""
    __slots__ = ("name", "min_raw", "min_net", "size_scale", "log_only")

    def __init__(self, name: str, min_raw: float, min_net: float,
                 size_scale: float = 1.0, log_only: bool = False):
        self.name = name
        self.min_raw = min_raw
        self.min_net = min_net
        self.size_scale = size_scale
        self.log_only = log_only


_DEFAULT_BANDS = [
    EdgeBand("strong",  0.08, 0.05, size_scale=1.0,  log_only=False),
    EdgeBand("normal",  0.05, 0.03, size_scale=0.7,  log_only=False),
    EdgeBand("observe", 0.03, 0.00, size_scale=0.0,  log_only=True),
]


class EdgeEngine:
    """Calculates raw and net edge, classifies into bands, decides if a trade is worth taking."""

    def __init__(self, cfg: dict[str, Any]):
        edge_cfg = cfg.get("edge", {})
        self.fee_rate: float = edge_cfg.get("fee_rate", 0.02)
        self.slippage_est: float = edge_cfg.get("slippage_estimate", 0.01)
        self.uncertainty_weight: float = edge_cfg.get("uncertainty_penalty_weight", 0.5)

        bands_cfg = edge_cfg.get("bands")
        if bands_cfg and isinstance(bands_cfg, list):
            self.bands = [
                EdgeBand(
                    name=b.get("name", f"band_{i}"),
                    min_raw=b.get("min_raw_edge", 0.05),
                    min_net=b.get("min_net_edge", 0.03),
                    size_scale=b.get("size_scale", 1.0),
                    log_only=b.get("log_only", False),
                )
                for i, b in enumerate(bands_cfg)
            ]
        else:
            self.bands = list(_DEFAULT_BANDS)

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

        band = self._classify_band(raw_edge, net_edge)
        execution_allowed = band is not None and not band.log_only
        size_scale = band.size_scale if band else 0.0
        band_name = band.name if band else "below_threshold"

        reasons = []
        if band is None:
            reasons.append(f"raw_edge {raw_edge:.4f} below all bands")
        elif band.log_only:
            reasons.append(f"band '{band.name}' is observe-only")

        decision_reason = (
            f"Side: {side}. Band: {band_name}. "
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
            edge_band=band_name,
            size_scale=round(size_scale, 2),
        )

    def _classify_band(self, raw_edge: float, net_edge: float) -> EdgeBand | None:
        """Find the highest band that raw + net edge qualifies for."""
        for band in self.bands:
            if raw_edge >= band.min_raw and net_edge >= band.min_net:
                return band
        return None
