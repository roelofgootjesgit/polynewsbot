"""
Probability engine — rule-based probability update given news + market context.
Fase 6 adds LLM-based interpretation.
"""
import logging
from typing import Any

from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.markets import MarketCandidate
from src.models.probability import ProbabilityAssessment
from src.resolution.parser import ResolutionMatch

logger = logging.getLogger(__name__)

_POSITIVE_KEYWORDS = [
    "approve", "pass", "sign", "confirm", "announce", "launch", "win",
    "surge", "soar", "rise", "jump", "rally", "break", "exceed", "beat",
    "accept", "agree", "adopt", "enact", "ratify", "green light",
]
_NEGATIVE_KEYWORDS = [
    "reject", "deny", "block", "fail", "lose", "drop", "fall", "crash",
    "decline", "cancel", "withdraw", "veto", "oppose", "ban", "suspend",
    "delay", "postpone", "collapse",
]


class ProbabilityEngine:
    """Rule-based probability update engine."""

    def __init__(self, cfg: dict[str, Any]):
        prob_cfg = cfg.get("probability", {})
        self.method: str = prob_cfg.get("method", "rule_based")
        self.min_confidence: float = prob_cfg.get("min_confidence", 0.4)

    def assess(
        self,
        event: NormalizedNewsEvent,
        market: MarketCandidate,
        resolution_match: ResolutionMatch,
        current_market_prob: float,
    ) -> ProbabilityAssessment:
        """Produce a probability assessment for a market given a news event."""
        direction = _detect_direction(event.headline)
        source_quality = event.source_reliability_score
        novelty = event.novelty_hint if event.novelty_hint is not None else 0.6
        res_match = resolution_match.match_score

        shift = _calculate_shift(
            direction=direction,
            source_quality=source_quality,
            novelty=novelty,
            resolution_match=res_match,
        )

        model_prob = max(0.01, min(0.99, current_market_prob + shift))

        confidence = _calculate_confidence(
            source_tier=event.source_tier,
            resolution_match=res_match,
            novelty=novelty,
        )

        already_priced = 0.3 if novelty < 0.4 else 0.1

        reasoning = (
            f"Direction: {direction}. "
            f"Shift: {shift:+.3f}. "
            f"Source: {event.source_name} (tier {event.source_tier.value}, quality {source_quality:.2f}). "
            f"Resolution match: {res_match:.2f}. "
            f"Novelty: {novelty:.2f}."
        )

        return ProbabilityAssessment(
            event_id=event.event_id,
            market_id=market.market_id,
            model_probability=round(model_prob, 4),
            confidence_score=round(confidence, 4),
            source_quality_score=round(source_quality, 4),
            novelty_score=round(novelty, 4),
            resolution_match_score=round(res_match, 4),
            already_priced_risk=round(already_priced, 4),
            reasoning_summary=reasoning,
            method=self.method,
            claim_direction=direction,
        )


def _detect_direction(headline: str) -> str:
    """Detect if headline is positive, negative, or neutral for YES."""
    lower = headline.lower()
    pos = sum(1 for kw in _POSITIVE_KEYWORDS if kw in lower)
    neg = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in lower)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _calculate_shift(
    direction: str,
    source_quality: float,
    novelty: float,
    resolution_match: float,
) -> float:
    """Calculate probability shift based on signal components."""
    base_shift = 0.0
    if direction == "positive":
        base_shift = 0.08
    elif direction == "negative":
        base_shift = -0.08

    quality_mult = 0.5 + source_quality * 0.5
    novelty_mult = 0.3 + novelty * 0.7
    res_mult = 0.2 + resolution_match * 0.8

    shift = base_shift * quality_mult * novelty_mult * res_mult
    return round(shift, 4)


def _calculate_confidence(
    source_tier: SourceTier,
    resolution_match: float,
    novelty: float,
) -> float:
    """Calculate confidence in the probability estimate."""
    tier_score = {1: 0.9, 2: 0.7, 3: 0.45, 4: 0.2}.get(source_tier.value, 0.3)
    confidence = (tier_score * 0.4 + resolution_match * 0.4 + novelty * 0.2)
    return min(max(confidence, 0.0), 1.0)
