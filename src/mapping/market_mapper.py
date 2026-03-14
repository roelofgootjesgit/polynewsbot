"""
Market mapper — maps a news event to relevant Polymarket markets.
Two-step approach: 1) topic → market cluster, 2) cluster → ranked candidates.
"""
import logging
from difflib import SequenceMatcher
from typing import Any, Optional

from src.models.events import NormalizedNewsEvent
from src.models.markets import MarketCandidate
from src.mapping.universe import MarketUniverse

logger = logging.getLogger(__name__)


class MappingResult:
    """Result of mapping a news event to markets."""
    __slots__ = ("candidates", "best", "cluster_id")

    def __init__(self):
        self.candidates: list[tuple[MarketCandidate, float]] = []  # (market, confidence)
        self.best: Optional[MarketCandidate] = None
        self.cluster_id: Optional[str] = None


class MarketMapper:
    """Maps news events to Polymarket markets."""

    def __init__(self, cfg: dict[str, Any], universe: MarketUniverse):
        map_cfg = cfg.get("mapping", {})
        self.min_confidence: float = map_cfg.get("min_mapping_confidence", 0.6)
        self.min_liquidity: float = map_cfg.get("min_liquidity_score", 0.3)
        self.max_candidates: int = map_cfg.get("max_markets_per_event", 3)
        self._universe = universe

    def map_event(self, event: NormalizedNewsEvent) -> MappingResult:
        """Map a news event to the most relevant markets."""
        result = MappingResult()

        search_terms = self._build_search_terms(event)
        candidates: list[tuple[MarketCandidate, float]] = []

        for term in search_terms:
            matches = self._universe.search(term)
            for market in matches:
                conf = self._score_match(event, market, term)
                if conf >= self.min_confidence and market.liquidity_score >= self.min_liquidity:
                    candidates.append((market, conf))

        candidates = _deduplicate(candidates)
        candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = candidates[:self.max_candidates]

        result.candidates = candidates
        if candidates:
            result.best = candidates[0][0]
            result.cluster_id = candidates[0][0].event_cluster_id

        logger.debug(
            "Mapped '%s' → %d candidates (best: %s, conf: %.2f)",
            event.headline[:50],
            len(candidates),
            result.best.market_title[:40] if result.best else "none",
            candidates[0][1] if candidates else 0.0,
        )
        return result

    def _build_search_terms(self, event: NormalizedNewsEvent) -> list[str]:
        """Extract search terms from event headline and topics."""
        terms: list[str] = []

        terms.extend(event.topic_hints)

        headline = event.headline.lower()
        for keyword in _KEY_ENTITIES:
            if keyword in headline:
                terms.append(keyword)

        words = event.headline.split()
        if len(words) >= 3:
            terms.append(" ".join(words[:4]))

        return list(dict.fromkeys(terms))

    def _score_match(
        self,
        event: NormalizedNewsEvent,
        market: MarketCandidate,
        search_term: str,
    ) -> float:
        """Score how well a news event matches a market."""
        title_lower = market.market_title.lower()
        headline_lower = event.headline.lower()

        title_sim = SequenceMatcher(None, headline_lower, title_lower).ratio()

        keyword_hits = 0
        event_words = set(headline_lower.split())
        market_words = set(title_lower.split())
        common = event_words & market_words - _STOPWORDS
        keyword_hits = len(common)

        keyword_score = min(keyword_hits * 0.15, 0.6)
        similarity_score = title_sim

        topic_bonus = 0.0
        if event.topic_hints and market.market_category:
            if market.market_category in event.topic_hints:
                topic_bonus = 0.15

        liquidity_bonus = market.liquidity_score * 0.1

        confidence = min(
            keyword_score + similarity_score * 0.5 + topic_bonus + liquidity_bonus,
            1.0,
        )
        return round(confidence, 3)


def _deduplicate(
    candidates: list[tuple[MarketCandidate, float]],
) -> list[tuple[MarketCandidate, float]]:
    """Keep highest confidence per market_id."""
    seen: dict[str, tuple[MarketCandidate, float]] = {}
    for market, conf in candidates:
        key = market.condition_id or market.market_id
        if key not in seen or conf > seen[key][1]:
            seen[key] = (market, conf)
    return list(seen.values())


_KEY_ENTITIES = [
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
    "trump", "biden", "harris", "election", "president",
    "fed", "fomc", "interest rate", "rate cut", "rate hike",
    "cpi", "inflation", "gdp", "jobs", "unemployment",
    "sec", "etf", "regulation",
    "war", "russia", "ukraine", "china", "tariff",
]

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "will", "would", "could", "should", "may", "might", "can",
    "in", "on", "at", "to", "for", "of", "by", "with", "from",
    "and", "or", "but", "not", "no", "if", "then", "than",
    "this", "that", "it", "its", "has", "have", "had",
    "do", "does", "did", "more", "most", "very", "so",
}
