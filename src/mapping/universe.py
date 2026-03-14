"""
Market universe — fetches, caches, and filters Polymarket events/markets.
Provides the tradeable market universe for the bot.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.models.markets import MarketCandidate

logger = logging.getLogger(__name__)

_CACHE_FILE = Path("data/market_universe_cache.json")


class MarketUniverse:
    """Manages the set of markets the bot is allowed to trade."""

    def __init__(self, cfg: dict[str, Any]):
        map_cfg = cfg.get("mapping", {})
        filter_cfg = cfg.get("filter", {})

        self.min_liquidity: float = map_cfg.get("min_liquidity_score", 0.3)
        self.categories: list[str] = filter_cfg.get("categories", [])
        self._events: list[dict[str, Any]] = []
        self._markets: list[MarketCandidate] = []

    def load_from_api(self, client: Any) -> int:
        """Fetch all active events from Polymarket and build market list."""
        from src.execution.polymarket_client import PolymarketClient
        assert isinstance(client, PolymarketClient)

        raw_events = client.get_all_active_events()
        self._events = raw_events
        self._markets = []

        for event in raw_events:
            markets = event.get("markets", [])
            event_slug = event.get("slug", "")
            event_tags = [t.get("label", "").lower() for t in event.get("tags", [])]

            for mkt in markets:
                if not mkt.get("enableOrderBook", False):
                    continue

                candidate = _parse_market(mkt, event_slug, event_tags)
                if candidate:
                    self._markets.append(candidate)

        logger.info(
            "Universe loaded: %d events → %d tradeable markets",
            len(raw_events), len(self._markets),
        )
        return len(self._markets)

    def get_markets(self, category: Optional[str] = None) -> list[MarketCandidate]:
        """Get all markets, optionally filtered by category."""
        if category:
            return [m for m in self._markets if m.market_category == category]
        return list(self._markets)

    def find_by_id(self, market_id: str) -> Optional[MarketCandidate]:
        """Find a specific market by condition_id or market_id."""
        for m in self._markets:
            if m.market_id == market_id or m.condition_id == market_id:
                return m
        return None

    def search(self, query: str) -> list[MarketCandidate]:
        """Simple keyword search across market titles."""
        q = query.lower()
        return [m for m in self._markets if q in m.market_title.lower()]

    def save_cache(self) -> None:
        """Cache current universe to disk."""
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = [m.model_dump(mode="json") for m in self._markets]
        _CACHE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Universe cached: %d markets → %s", len(data), _CACHE_FILE)

    def load_cache(self) -> int:
        """Load universe from disk cache."""
        if not _CACHE_FILE.exists():
            logger.warning("No cache file found at %s", _CACHE_FILE)
            return 0
        raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        self._markets = [MarketCandidate.model_validate(m) for m in raw]
        logger.info("Universe loaded from cache: %d markets", len(self._markets))
        return len(self._markets)


def _parse_market(
    mkt: dict[str, Any],
    event_slug: str,
    event_tags: list[str],
) -> Optional[MarketCandidate]:
    """Parse a Gamma API market dict into a MarketCandidate."""
    try:
        condition_id = mkt.get("conditionId", "")
        question = mkt.get("question", mkt.get("groupItemTitle", ""))
        description = mkt.get("description", "")

        tokens = mkt.get("clobTokenIds", [])
        yes_token = tokens[0] if tokens else ""

        end_date_str = mkt.get("endDate") or mkt.get("end_date_iso")
        deadline = None
        if end_date_str:
            try:
                deadline = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        volume = float(mkt.get("volume", 0) or 0)
        liquidity = float(mkt.get("liquidity", 0) or 0)
        liquidity_score = min(liquidity / 100_000, 1.0) if liquidity > 0 else 0.0

        category = event_tags[0] if event_tags else None

        return MarketCandidate(
            market_id=yes_token or condition_id,
            condition_id=condition_id,
            market_title=question,
            market_category=category,
            resolution_text=description,
            deadline=deadline,
            active=True,
            liquidity_score=liquidity_score,
            event_cluster_id=event_slug,
        )
    except Exception:
        logger.debug("Failed to parse market: %s", mkt.get("question", "?"))
        return None
