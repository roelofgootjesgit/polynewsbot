"""
Position sizing — determines how much capital to allocate to a trade.
Prediction market sizing: risk = share price * shares (no leverage).
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculates position size based on capital and risk limits."""

    def __init__(self, cfg: dict[str, Any]):
        risk_cfg = cfg.get("risk", {})
        self.max_position_pct: float = risk_cfg.get("max_position_pct", 0.02)
        self.max_cluster_pct: float = risk_cfg.get("max_cluster_pct", 0.05)
        self.max_total_pct: float = risk_cfg.get("max_total_exposure_pct", 0.20)

    def calculate(
        self,
        capital: float,
        price: float,
        confidence: float,
        cluster_exposure: float = 0.0,
        total_exposure: float = 0.0,
    ) -> float:
        """Calculate position size in USD.

        Returns 0.0 if any exposure limit would be breached.
        """
        if capital <= 0 or price <= 0 or price >= 1.0:
            return 0.0

        max_trade_usd = capital * self.max_position_pct
        remaining_cluster = max(0, capital * self.max_cluster_pct - cluster_exposure)
        remaining_total = max(0, capital * self.max_total_pct - total_exposure)

        size_usd = min(max_trade_usd, remaining_cluster, remaining_total)

        confidence_scale = 0.5 + confidence * 0.5
        size_usd *= confidence_scale

        size_usd = max(0.0, round(size_usd, 2))

        logger.debug(
            "Sizing: capital=%.0f, price=%.4f, conf=%.2f → $%.2f "
            "(max_trade=$%.2f, cluster_remaining=$%.2f, total_remaining=$%.2f)",
            capital, price, confidence, size_usd,
            max_trade_usd, remaining_cluster, remaining_total,
        )
        return size_usd
