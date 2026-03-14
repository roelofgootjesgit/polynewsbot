"""
Market state analyzer — reads orderbook and computes tradability metrics.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from src.models.markets import MarketState, OrderBookLevel

logger = logging.getLogger(__name__)


class MarketStateAnalyzer:
    """Analyzes orderbook data to produce MarketState assessments."""

    def __init__(self, cfg: dict[str, Any]):
        risk_cfg = cfg.get("risk", {})
        self.max_spread: float = risk_cfg.get("max_spread", 0.10)

    def analyze(self, market_id: str, orderbook: dict[str, Any]) -> MarketState:
        """Convert raw orderbook response into a MarketState assessment."""
        bids = _parse_levels(orderbook.get("bids", []), descending=True)
        asks = _parse_levels(orderbook.get("asks", []), descending=False)

        best_bid = bids[0].price if bids else None
        best_ask = asks[0].price if asks else None
        spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None
        mid = ((best_bid + best_ask) / 2) if spread is not None else None

        total_bid_liq = sum(l.price * l.size for l in bids)
        total_ask_liq = sum(l.price * l.size for l in asks)

        slippage = _estimate_slippage(asks, target_size=50.0)
        quality = _assess_quality(spread, total_bid_liq, total_ask_liq, self.max_spread)

        return MarketState(
            market_id=market_id,
            timestamp=datetime.now(timezone.utc),
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            mid_price=mid,
            implied_probability=mid,
            bid_depth=bids[:10],
            ask_depth=asks[:10],
            total_bid_liquidity=total_bid_liq,
            total_ask_liquidity=total_ask_liq,
            estimated_slippage_bps=slippage,
            liquidity_quality=quality,
        )


def _parse_levels(raw_levels: list[dict], descending: bool = True) -> list[OrderBookLevel]:
    """Parse raw orderbook levels into OrderBookLevel objects, sorted by price."""
    levels = []
    for lvl in raw_levels:
        try:
            levels.append(OrderBookLevel(
                price=float(lvl.get("price", 0)),
                size=float(lvl.get("size", 0)),
            ))
        except (ValueError, TypeError):
            continue
    levels.sort(key=lambda x: x.price, reverse=descending)
    return levels


def _estimate_slippage(asks: list[OrderBookLevel], target_size: float) -> float:
    """Estimate slippage in basis points for buying target_size shares."""
    if not asks or target_size <= 0:
        return 0.0

    best_price = asks[0].price if asks else 0
    if best_price <= 0:
        return 0.0

    filled = 0.0
    total_cost = 0.0
    for level in asks:
        fill_at_level = min(level.size, target_size - filled)
        total_cost += fill_at_level * level.price
        filled += fill_at_level
        if filled >= target_size:
            break

    if filled <= 0:
        return 999.0

    avg_price = total_cost / filled
    slippage_bps = ((avg_price - best_price) / best_price) * 10_000
    return round(slippage_bps, 1)


def _assess_quality(
    spread: float | None,
    bid_liq: float,
    ask_liq: float,
    max_spread: float,
) -> str:
    """Classify liquidity quality as high/medium/low."""
    total = bid_liq + ask_liq
    if spread is None or spread > max_spread:
        return "low"
    if total > 10_000 and spread < max_spread * 0.5:
        return "high"
    if total > 1_000:
        return "medium"
    return "low"
