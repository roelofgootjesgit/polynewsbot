"""
LLM-based probability engine — uses structured prompts for probability assessment.
Falls back to rule-based engine on failure.
"""
import logging
from typing import Any

from src.ai.llm_client import LLMClient
from src.ai.prompts import PROBABILITY_SYSTEM, PROBABILITY_USER
from src.models.events import NormalizedNewsEvent
from src.models.markets import MarketCandidate
from src.models.probability import ProbabilityAssessment
from src.resolution.parser import ResolutionMatch

logger = logging.getLogger(__name__)


class LLMProbabilityEngine:
    """LLM-based probability assessment."""

    def __init__(self, llm: LLMClient):
        self._llm = llm

    def assess(
        self,
        event: NormalizedNewsEvent,
        market: MarketCandidate,
        resolution_match: ResolutionMatch,
        current_market_prob: float,
    ) -> ProbabilityAssessment:
        """Get LLM probability assessment. Raises on failure."""
        body_text = event.raw_text or event.summary or ""
        body_section = f"Body: {body_text[:500]}" if body_text else ""

        user_prompt = PROBABILITY_USER.format(
            headline=event.headline,
            source_name=event.source_name,
            source_tier=event.source_tier.value,
            reliability=event.source_reliability_score,
            published_at=event.published_at or "unknown",
            topics=", ".join(event.topic_hints) if event.topic_hints else "none",
            body_section=body_section,
            market_title=market.market_title,
            resolution_text=market.resolution_text[:400],
            deadline=market.deadline or "none",
            current_prob=current_market_prob,
        )

        data, usage = self._llm.chat_json(PROBABILITY_SYSTEM, user_prompt)

        prob = _clamp(float(data.get("probability", current_market_prob)), 0.01, 0.99)
        conf = _clamp(float(data.get("confidence", 0.5)), 0.0, 1.0)
        direction = data.get("direction", "neutral")
        reasoning = data.get("reasoning", "LLM assessment")
        already_priced = _clamp(float(data.get("already_priced_risk", 0.2)), 0.0, 1.0)

        reasoning_full = (
            f"[LLM] {reasoning} "
            f"(tokens={usage.total_tokens}, cost=${usage.estimated_cost_usd:.4f})"
        )

        return ProbabilityAssessment(
            event_id=event.event_id,
            market_id=market.market_id,
            model_probability=round(prob, 4),
            confidence_score=round(conf, 4),
            source_quality_score=round(event.source_reliability_score, 4),
            novelty_score=round(event.novelty_hint or 0.6, 4),
            resolution_match_score=round(resolution_match.match_score, 4),
            already_priced_risk=round(already_priced, 4),
            reasoning_summary=reasoning_full,
            method="llm",
            claim_direction=direction if direction in ("positive", "negative", "neutral") else "neutral",
        )


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
