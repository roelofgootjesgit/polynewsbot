"""
Normalized news event models — the internal standard for all news flowing through the pipeline.
"""
from datetime import datetime
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field


class SourceTier(IntEnum):
    """Source reliability tier. Lower = more authoritative."""
    TIER_1_PRIMARY = 1       # official sources, central banks, court docs, filings
    TIER_2_TRUSTED_MEDIA = 2 # major wire services, established financial press
    TIER_3_SECONDARY = 3     # analysts, blogs, opinion, summaries
    TIER_4_RUMOR = 4         # unconfirmed social posts, screenshots, speculation


class RawNewsItem(BaseModel):
    """Raw news item as received from a source, before normalization."""
    source_name: str
    headline: str
    body: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_data: Optional[dict] = None


class NormalizedNewsEvent(BaseModel):
    """
    The single internal standard for all news events in the pipeline.
    Every module downstream receives this object — never raw source data.
    """
    event_id: str = Field(description="Unique event identifier (UUID)")
    received_at: datetime = Field(description="Timestamp when bot received this event")
    published_at: Optional[datetime] = Field(None, description="Original publication time")

    source_name: str
    source_tier: SourceTier
    source_reliability_score: float = Field(ge=0.0, le=1.0)

    headline: str
    summary: Optional[str] = None
    raw_text: Optional[str] = None
    url: Optional[str] = None
    language: str = "en"

    topic_hints: list[str] = Field(default_factory=list)
    novelty_hint: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="0.0 = old news rehashed, 1.0 = completely new information",
    )

    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
