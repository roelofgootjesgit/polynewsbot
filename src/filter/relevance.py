"""
Relevance filter — determines if a news event is worth processing.
Three dimensions: semantic relevance, time relevance, combined score.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.models.events import NormalizedNewsEvent

logger = logging.getLogger(__name__)


class RelevanceResult:
    """Result of a relevance check."""
    __slots__ = ("passed", "score", "semantic_score", "time_score", "reasons")

    def __init__(self):
        self.passed: bool = False
        self.score: float = 0.0
        self.semantic_score: float = 0.0
        self.time_score: float = 0.0
        self.reasons: list[str] = []


class RelevanceFilter:
    """Filters news events on relevance before they enter the mapping pipeline."""

    def __init__(self, cfg: dict[str, Any]):
        filter_cfg = cfg.get("filter", {})
        self.min_score: float = filter_cfg.get("min_relevance_score", 0.5)
        self.max_age_minutes: int = filter_cfg.get("max_age_minutes", 15)
        self.categories: list[str] = filter_cfg.get("categories", [])
        self.whitelist: list[str] = [k.lower() for k in filter_cfg.get("keywords_whitelist", [])]
        self.blacklist: list[str] = [k.lower() for k in filter_cfg.get("keywords_blacklist", [])]

    def check(self, event: NormalizedNewsEvent) -> RelevanceResult:
        """Evaluate relevance of a single event."""
        result = RelevanceResult()

        if event.is_duplicate:
            result.reasons.append("duplicate")
            return result

        result.semantic_score = self._semantic_score(event)
        result.time_score = self._time_score(event)

        result.score = (result.semantic_score * 0.7) + (result.time_score * 0.3)
        result.passed = result.score >= self.min_score

        if not result.passed:
            result.reasons.append(f"score {result.score:.2f} < {self.min_score:.2f}")

        return result

    def filter_batch(self, events: list[NormalizedNewsEvent]) -> list[NormalizedNewsEvent]:
        """Filter a batch, returning only events that pass relevance check."""
        passed = []
        for event in events:
            result = self.check(event)
            if result.passed:
                passed.append(event)
            else:
                logger.debug(
                    "Filtered out: %s (score=%.2f, reasons=%s)",
                    event.headline[:60], result.score, result.reasons,
                )
        logger.info("Relevance filter: %d/%d events passed", len(passed), len(events))
        return passed

    def _semantic_score(self, event: NormalizedNewsEvent) -> float:
        """Score based on topic overlap with configured categories + keyword matching."""
        headline_lower = event.headline.lower()

        if any(kw in headline_lower for kw in self.blacklist):
            return 0.0

        score = 0.0

        if self.whitelist and any(kw in headline_lower for kw in self.whitelist):
            score = 1.0
            return score

        if event.topic_hints and self.categories:
            overlap = set(event.topic_hints) & set(self.categories)
            if overlap:
                score = min(len(overlap) * 0.4 + 0.3, 1.0)

        if score == 0.0 and event.topic_hints:
            score = 0.3

        tier_boost = max(0, (5 - event.source_tier)) * 0.05
        score = min(score + tier_boost, 1.0)

        return score

    def _time_score(self, event: NormalizedNewsEvent) -> float:
        """Score based on freshness. 1.0 = just published, 0.0 = too old."""
        if not event.published_at:
            return 0.5  # unknown age — moderate score

        now = datetime.now(timezone.utc)
        pub = event.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)

        age_minutes = (now - pub).total_seconds() / 60

        if age_minutes <= 0:
            return 1.0
        if age_minutes >= self.max_age_minutes:
            return 0.0

        return 1.0 - (age_minutes / self.max_age_minutes)
