"""
Resolution parser — rule-based interpretation of market resolution text.
Extracts structured criteria and scores how well a news event matches.

Fase 6 adds LLM-based parsing for complex resolution texts.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.models.events import NormalizedNewsEvent
from src.models.markets import MarketCandidate

logger = logging.getLogger(__name__)


class ResolutionCriteria(BaseModel):
    """Structured interpretation of a market's resolution text."""
    market_id: str
    resolution_text: str
    has_deadline: bool = False
    deadline: Optional[datetime] = None
    requires_official_source: bool = False
    key_phrases: list[str] = Field(default_factory=list)
    resolution_type: str = "unknown"  # binary, threshold, date, multi_outcome
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class ResolutionMatch(BaseModel):
    """How well a news event matches a market's resolution criteria."""
    event_id: str
    market_id: str
    match_score: float = Field(0.0, ge=0.0, le=1.0)
    matched_phrases: list[str] = Field(default_factory=list)
    reasoning: str = ""
    sufficient_for_trade: bool = False


class ResolutionParser:
    """Rule-based resolution text parser."""

    def __init__(self, cfg: dict[str, Any]):
        res_cfg = cfg.get("resolution", {})
        self.min_confidence: float = res_cfg.get("min_understanding_confidence", 0.7)

    def parse_criteria(self, market: MarketCandidate) -> ResolutionCriteria:
        """Extract structured criteria from a market's resolution text."""
        text = market.resolution_text or ""
        text_lower = text.lower()

        key_phrases = _extract_key_phrases(text)
        has_deadline = bool(market.deadline) or _has_date_reference(text_lower)
        requires_official = _requires_official_source(text_lower)
        res_type = _detect_resolution_type(text_lower)

        phrase_count = len(key_phrases)
        confidence = min(0.3 + phrase_count * 0.1 + (0.1 if has_deadline else 0) + (0.1 if res_type != "unknown" else 0), 1.0)

        return ResolutionCriteria(
            market_id=market.market_id,
            resolution_text=text[:500],
            has_deadline=has_deadline,
            deadline=market.deadline,
            requires_official_source=requires_official,
            key_phrases=key_phrases,
            resolution_type=res_type,
            confidence=confidence,
        )

    def match_event(
        self,
        event: NormalizedNewsEvent,
        criteria: ResolutionCriteria,
    ) -> ResolutionMatch:
        """Score how well a news event matches the resolution criteria."""
        headline_lower = event.headline.lower()
        body_lower = (event.raw_text or event.summary or "").lower()
        combined = headline_lower + " " + body_lower

        matched = []
        for phrase in criteria.key_phrases:
            if phrase.lower() in combined:
                matched.append(phrase)

        phrase_score = len(matched) / max(len(criteria.key_phrases), 1)

        type_bonus = 0.0
        if criteria.resolution_type in ("binary", "threshold"):
            type_bonus = 0.1

        source_penalty = 0.0
        if criteria.requires_official_source and event.source_tier.value >= 3:
            source_penalty = -0.2

        score = min(max(phrase_score * 0.7 + type_bonus + source_penalty + 0.1, 0.0), 1.0)

        sufficient = (
            score >= self.min_confidence
            and criteria.confidence >= 0.4
            and len(matched) >= 1
        )

        reasoning = (
            f"Matched {len(matched)}/{len(criteria.key_phrases)} key phrases. "
            f"Resolution type: {criteria.resolution_type}. "
            f"Source tier: {event.source_tier.value}."
        )

        return ResolutionMatch(
            event_id=event.event_id,
            market_id=criteria.market_id,
            match_score=round(score, 3),
            matched_phrases=matched,
            reasoning=reasoning,
            sufficient_for_trade=sufficient,
        )


def _extract_key_phrases(text: str) -> list[str]:
    """Extract actionable phrases from resolution text."""
    phrases = []
    patterns = [
        r"resolves?\s+(?:to\s+)?[\"']?(yes|no)[\"']?\s+if\s+(.+?)(?:\.|$)",
        r"will\s+resolve\s+(?:to\s+)?[\"']?(yes|no)[\"']?\s+if\s+(.+?)(?:\.|$)",
        r"(?:market|this)\s+will\s+(.+?)(?:\.|$)",
    ]
    text_lower = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            phrase = match.group(match.lastindex or 1).strip()
            if len(phrase) > 5 and phrase not in phrases:
                phrases.append(phrase[:200])

    for keyword in _RESOLUTION_KEYWORDS:
        if keyword in text_lower and keyword not in " ".join(phrases):
            phrases.append(keyword)

    return phrases[:10]


def _has_date_reference(text: str) -> bool:
    return bool(re.search(
        r"(by|before|until|deadline|end of|january|february|march|april|may|june|"
        r"july|august|september|october|november|december|\d{4})",
        text, re.IGNORECASE,
    ))


def _requires_official_source(text: str) -> bool:
    return bool(re.search(
        r"(official|officially|announce|confirmed|published|signed|enacted|"
        r"according to|reported by|government|federal|agency)",
        text, re.IGNORECASE,
    ))


def _detect_resolution_type(text: str) -> str:
    if re.search(r"(above|below|reach\w*|exceed\w*|more than|less than|over|under)\s+\$?[\d,]", text):
        return "threshold"
    if re.search(r"(yes|no)\b.*\b(yes|no)", text):
        return "binary"
    if re.search(r"(who will|which|winner)", text):
        return "multi_outcome"
    if re.search(r"(by|before|until)\s+\w+\s+\d{1,2}", text):
        return "date"
    return "unknown"


_RESOLUTION_KEYWORDS = [
    "announce", "approve", "sign", "pass", "reject", "confirm",
    "reach", "exceed", "drop", "rise", "fall", "increase", "decrease",
    "win", "lose", "elect", "nominate", "resign", "impeach",
    "ban", "regulate", "launch", "release", "publish",
]
