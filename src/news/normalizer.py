"""
News normalizer — converts RawNewsItem to NormalizedNewsEvent.
Handles source tier assignment, reliability scoring, and deduplication.
"""
import hashlib
import logging
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from src.models.events import NormalizedNewsEvent, RawNewsItem, SourceTier

logger = logging.getLogger(__name__)

_DEFAULT_RELIABILITY = {
    SourceTier.TIER_1_PRIMARY: 0.95,
    SourceTier.TIER_2_TRUSTED_MEDIA: 0.80,
    SourceTier.TIER_3_SECONDARY: 0.55,
    SourceTier.TIER_4_RUMOR: 0.25,
}


class NewsNormalizer:
    """Normalizes raw news items and deduplicates."""

    def __init__(self, cfg: dict[str, Any]):
        news_cfg = cfg.get("news", {})
        tier_cfg = news_cfg.get("source_tiers", {})

        self._reliability: dict[SourceTier, float] = {
            SourceTier.TIER_1_PRIMARY: tier_cfg.get("tier_1_reliability", 0.95),
            SourceTier.TIER_2_TRUSTED_MEDIA: tier_cfg.get("tier_2_reliability", 0.80),
            SourceTier.TIER_3_SECONDARY: tier_cfg.get("tier_3_reliability", 0.55),
            SourceTier.TIER_4_RUMOR: tier_cfg.get("tier_4_reliability", 0.25),
        }

        self._seen: OrderedDict[str, str] = OrderedDict()
        self._max_seen = 5000

    def normalize(
        self,
        item: RawNewsItem,
        source_tier: SourceTier,
    ) -> NormalizedNewsEvent:
        """Convert a RawNewsItem into a NormalizedNewsEvent."""
        event_id = str(uuid.uuid4())
        dedup_hash = _headline_hash(item.headline)

        is_dup = dedup_hash in self._seen
        dup_of = self._seen.get(dedup_hash)

        if not is_dup:
            self._seen[dedup_hash] = event_id
            if len(self._seen) > self._max_seen:
                self._seen.popitem(last=False)

        reliability = self._reliability.get(source_tier, 0.5)
        topics = _extract_topic_hints(item.headline)

        return NormalizedNewsEvent(
            event_id=event_id,
            received_at=datetime.now(timezone.utc),
            published_at=item.published_at,
            source_name=item.source_name,
            source_tier=source_tier,
            source_reliability_score=reliability,
            headline=item.headline,
            summary=item.body,
            raw_text=item.body,
            url=item.url,
            topic_hints=topics,
            is_duplicate=is_dup,
            duplicate_of=dup_of,
        )

    def normalize_batch(
        self,
        items: list[RawNewsItem],
        source_tier: SourceTier,
    ) -> list[NormalizedNewsEvent]:
        """Normalize a batch of items, returning all (including duplicates marked)."""
        return [self.normalize(item, source_tier) for item in items]

    def reset_seen(self) -> None:
        """Clear the deduplication cache."""
        self._seen.clear()

    @property
    def seen_count(self) -> int:
        return len(self._seen)


def _headline_hash(headline: str) -> str:
    """Create a dedup hash from a headline (lowercased, stripped)."""
    normalized = headline.lower().strip()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]


_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "crypto": ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", "token", "defi"],
    "politics": ["election", "president", "congress", "senate", "vote", "democrat", "republican", "trump", "biden"],
    "economics": ["gdp", "inflation", "cpi", "unemployment", "jobs", "recession", "growth"],
    "central_banks": ["fed", "federal reserve", "rate", "fomc", "ecb", "boj", "interest rate", "monetary"],
    "regulation": ["sec", "regulation", "ban", "approve", "ruling", "court", "law", "bill", "legislation"],
    "geopolitics": ["war", "sanction", "tariff", "nato", "conflict", "military", "invasion"],
}


def _extract_topic_hints(headline: str) -> list[str]:
    """Extract topic hints from a headline using keyword matching."""
    lower = headline.lower()
    topics = []
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            topics.append(topic)
    return topics
