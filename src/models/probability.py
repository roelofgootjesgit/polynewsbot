"""
Probability assessment model — output of the probability engine.
"""
from typing import Optional

from pydantic import BaseModel, Field


class ProbabilityAssessment(BaseModel):
    """
    Structured probability update for a market given a news event.
    This is not a prediction — it's a controlled probability update.
    """
    event_id: str = Field(description="Which news event triggered this assessment")
    market_id: str = Field(description="Which market this assessment is for")

    model_probability: float = Field(
        ge=0.0, le=1.0,
        description="Model's estimate of YES probability after this news",
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="How confident the model is in this probability estimate",
    )

    source_quality_score: float = Field(ge=0.0, le=1.0)
    novelty_score: float = Field(
        ge=0.0, le=1.0,
        description="0.0 = already known, 1.0 = completely new evidence",
    )
    resolution_match_score: float = Field(
        ge=0.0, le=1.0,
        description="How directly this news impacts the resolution criteria",
    )
    already_priced_risk: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Estimate of how much the market has already absorbed this info",
    )

    reasoning_summary: str = Field(
        description="Human-readable reasoning chain for audit",
    )
    method: str = Field(
        "rule_based",
        description="Which engine produced this: rule_based | llm | hybrid",
    )

    claim_direction: Optional[str] = Field(
        None, description="positive | negative | neutral — effect on YES probability",
    )
