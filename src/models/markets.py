"""
Polymarket market models — market metadata, state, and orderbook representation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MarketCandidate(BaseModel):
    """A Polymarket market that has been mapped to a news event."""
    market_id: str
    condition_id: str
    market_title: str
    market_category: Optional[str] = None
    resolution_text: str = Field(description="Official resolution criteria text")
    deadline: Optional[datetime] = None
    active: bool = True

    liquidity_score: float = Field(0.0, ge=0.0, le=1.0)
    mapping_confidence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="How confident the mapping from news to this market is",
    )
    event_cluster_id: Optional[str] = Field(
        None, description="Group of correlated markets on the same event",
    )


class OrderBookLevel(BaseModel):
    price: float
    size: float


class MarketState(BaseModel):
    """Current microstructure state of a market at a point in time."""
    market_id: str
    timestamp: datetime

    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread: Optional[float] = None
    mid_price: Optional[float] = None
    implied_probability: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Market-implied probability of YES (derived from mid price)",
    )

    bid_depth: list[OrderBookLevel] = Field(default_factory=list)
    ask_depth: list[OrderBookLevel] = Field(default_factory=list)
    total_bid_liquidity: float = 0.0
    total_ask_liquidity: float = 0.0

    recent_volume_24h: Optional[float] = None
    estimated_slippage_bps: Optional[float] = None
    liquidity_quality: Optional[str] = None  # "high", "medium", "low"
