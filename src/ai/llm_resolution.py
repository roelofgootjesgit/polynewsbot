"""
LLM-based resolution parser — understands complex resolution texts
and scores news-to-resolution matches using structured prompts.
"""
import logging
from typing import Any

from src.ai.llm_client import LLMClient
from src.ai.prompts import (
    RESOLUTION_SYSTEM, RESOLUTION_USER,
    RESOLUTION_MATCH_SYSTEM, RESOLUTION_MATCH_USER,
)
from src.models.events import NormalizedNewsEvent
from src.models.markets import MarketCandidate
from src.resolution.parser import ResolutionCriteria, ResolutionMatch

logger = logging.getLogger(__name__)


class LLMResolutionParser:
    """LLM-based resolution text interpreter."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def parse_criteria(self, market: MarketCandidate) -> ResolutionCriteria:
        """Use LLM to extract structured criteria from resolution text. Raises on failure."""
        user_prompt = RESOLUTION_USER.format(
            market_title=market.market_title,
            resolution_text=market.resolution_text[:800],
        )

        data, usage = self._llm.chat_json(RESOLUTION_SYSTEM, user_prompt)

        key_conditions = data.get("key_conditions", [])
        if not isinstance(key_conditions, list):
            key_conditions = [str(key_conditions)]

        res_type = data.get("resolution_type", "unknown")
        if res_type not in ("binary", "threshold", "date", "multi_outcome"):
            res_type = "unknown"

        confidence = _clamp(float(data.get("confidence", 0.5)), 0.0, 1.0)

        ambiguity = data.get("ambiguity_level", "medium")
        if ambiguity == "high":
            confidence *= 0.7

        return ResolutionCriteria(
            market_id=market.market_id,
            resolution_text=market.resolution_text[:500],
            has_deadline=bool(data.get("has_deadline", False)),
            deadline=market.deadline,
            requires_official_source=bool(data.get("requires_official_source", False)),
            key_phrases=key_conditions[:10],
            resolution_type=res_type,
            confidence=round(confidence, 3),
        )

    def match_event(
        self,
        event: NormalizedNewsEvent,
        criteria: ResolutionCriteria,
    ) -> ResolutionMatch:
        """Use LLM to score news-to-resolution match. Raises on failure."""
        body = event.raw_text or event.summary or event.headline
        user_prompt = RESOLUTION_MATCH_USER.format(
            headline=event.headline,
            source_name=event.source_name,
            source_tier=event.source_tier.value,
            body=body[:500],
            market_title="",
            resolution_text=criteria.resolution_text[:400],
            key_conditions=", ".join(criteria.key_phrases),
        )

        data, usage = self._llm.chat_json(RESOLUTION_MATCH_SYSTEM, user_prompt)

        score = _clamp(float(data.get("match_score", 0.0)), 0.0, 1.0)
        matched = data.get("matched_conditions", [])
        if not isinstance(matched, list):
            matched = [str(matched)] if matched else []
        reasoning = data.get("reasoning", "LLM match assessment")
        sufficient = bool(data.get("sufficient_for_resolution", False))

        return ResolutionMatch(
            event_id=event.event_id,
            market_id=criteria.market_id,
            match_score=round(score, 3),
            matched_phrases=matched[:10],
            reasoning=f"[LLM] {reasoning} (tokens={usage.total_tokens})",
            sufficient_for_trade=sufficient and score >= 0.5,
        )


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
