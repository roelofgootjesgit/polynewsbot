"""
Counter-news detector — checks if new headlines contradict
the thesis of existing open positions.

A position opened on "Fed approves rate cut" should be flagged
if a new headline says "Fed reverses rate cut decision".
"""
import logging
from typing import Any

from src.models.events import NormalizedNewsEvent
from src.models.trades import Position
from src.monitor.position_monitor import PositionMonitor

logger = logging.getLogger(__name__)

_CONTRADICTION_PAIRS = [
    ({"approve", "pass", "confirm", "sign", "accept", "agree"},
     {"reject", "deny", "block", "veto", "oppose", "reverse", "overturn"}),
    ({"rise", "surge", "rally", "jump", "soar", "increase", "gain"},
     {"fall", "crash", "drop", "decline", "plunge", "decrease", "lose"}),
    ({"launch", "announce", "release", "start", "begin"},
     {"cancel", "postpone", "delay", "suspend", "halt", "withdraw"}),
    ({"win", "elect", "nominate", "lead"},
     {"lose", "defeat", "resign", "step down", "withdraw"}),
]


class CounterNewsDetector:
    """Detects if incoming news contradicts open position theses."""

    def __init__(self, cfg: dict[str, Any]):
        self._min_source_tier_for_invalidation: int = cfg.get("risk", {}).get(
            "min_source_tier", 3
        )

    def check_against_positions(
        self,
        event: NormalizedNewsEvent,
        positions: list[Position],
        monitor: PositionMonitor,
    ) -> list[str]:
        """
        Check a new event against all open positions on the same market.
        Returns list of position_ids that were affected.
        """
        affected = []

        for pos in positions:
            if pos.status != "open":
                continue

            if not self._same_market_or_cluster(event, pos):
                continue

            contradiction = self._detect_contradiction(event, pos)
            if not contradiction:
                continue

            source_strong = event.source_tier.value <= self._min_source_tier_for_invalidation

            if source_strong:
                monitor.invalidate_thesis(
                    pos.position_id,
                    f"Counter-news from {event.source_name}: {event.headline[:80]}",
                )
                logger.warning(
                    "THESIS INVALIDATED: %s by '%s' (tier %d)",
                    pos.position_id, event.headline[:60], event.source_tier.value,
                )
            else:
                monitor.weaken_thesis(
                    pos.position_id,
                    f"Weak counter-signal from {event.source_name}: {event.headline[:80]}",
                )
                logger.info(
                    "THESIS WEAKENED: %s by '%s' (tier %d, not authoritative enough to invalidate)",
                    pos.position_id, event.headline[:60], event.source_tier.value,
                )

            affected.append(pos.position_id)

        return affected

    def _same_market_or_cluster(
        self, event: NormalizedNewsEvent, position: Position
    ) -> bool:
        """Check if event could be related to this position's market."""
        event_topics = set(t.lower() for t in (event.topic_hints or []))
        headline_lower = event.headline.lower()

        market_id_lower = position.market_id.lower()
        event_id_lower = position.event_id.lower()

        for topic in event_topics:
            if topic in market_id_lower or topic in event_id_lower:
                return True

        common_entities = _extract_entities(headline_lower)
        position_entities = _extract_entities(position.market_id.lower())
        if common_entities & position_entities:
            return True

        return False

    def _detect_contradiction(
        self, event: NormalizedNewsEvent, position: Position
    ) -> bool:
        """Detect if the event sentiment contradicts the position's side."""
        headline_lower = event.headline.lower()

        event_direction = _get_direction(headline_lower)
        if event_direction == "neutral":
            return False

        position_direction = "positive" if position.side == "YES" else "negative"

        return event_direction != position_direction


def _get_direction(text: str) -> str:
    """Get directional sentiment from text using contradiction pairs."""
    positive_hits = 0
    negative_hits = 0

    for pos_set, neg_set in _CONTRADICTION_PAIRS:
        for word in pos_set:
            if word in text:
                positive_hits += 1
        for word in neg_set:
            if word in text:
                negative_hits += 1

    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def _extract_entities(text: str) -> set[str]:
    """Extract likely entity keywords from text."""
    entities = set()
    for word in text.split():
        cleaned = word.strip(".,;:!?\"'()[]{}").lower()
        if len(cleaned) >= 4 and cleaned not in _STOP_WORDS:
            entities.add(cleaned)
    return entities


_STOP_WORDS = {
    "this", "that", "with", "from", "will", "have", "been", "they",
    "their", "what", "when", "where", "which", "there", "about",
    "would", "could", "should", "after", "before", "between",
    "market", "price", "trade", "order", "position",
}
