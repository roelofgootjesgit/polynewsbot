"""
Trade decision and position models.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TradeDecision(BaseModel):
    """
    Final trade decision produced by the edge engine + risk layer.
    """
    event_id: str
    market_id: str
    timestamp: datetime

    side: Literal["YES", "NO"]
    raw_edge: float = Field(description="model_prob - market_prob")
    net_edge: float = Field(description="raw_edge - fees - slippage - penalties")
    model_probability: float
    market_probability: float

    position_size_usd: float = Field(0.0, ge=0.0)
    limit_price: Optional[float] = None

    execution_allowed: bool = False
    guardrail_status: str = Field("pending", description="passed | vetoed | pending")
    veto_reasons: list[str] = Field(default_factory=list)
    decision_reason: str = ""

    confidence: float = Field(0.0, ge=0.0, le=1.0)
    source_tier: int = 1


class Position(BaseModel):
    """An open position being monitored for thesis validity."""
    position_id: str
    market_id: str
    event_id: str

    side: Literal["YES", "NO"]
    entry_price: float
    entry_timestamp: datetime
    shares: float
    cost_basis_usd: float

    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None

    original_model_probability: float
    original_confidence: float
    thesis_still_valid: bool = True
    exit_reason: Optional[str] = None

    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    realized_pnl: Optional[float] = None
    status: Literal["open", "closed", "pending"] = "pending"
