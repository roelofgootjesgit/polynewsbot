"""
Polymarket API client — wraps Gamma API (market data) and CLOB API (trading).

Gamma API: public REST, no auth → events, markets, metadata, resolution text.
CLOB API: py-clob-client → orderbook, prices, order placement, wallet signing.
"""
import logging
from typing import Any, Optional

import httpx
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Unified Polymarket client for both market data and trading."""

    def __init__(self, cfg: dict[str, Any]):
        pm_cfg = cfg.get("polymarket", {})
        self.base_url: str = pm_cfg.get("base_url", "https://clob.polymarket.com")
        self.gamma_url: str = pm_cfg.get("gamma_url", "https://gamma-api.polymarket.com")
        self.chain_id: int = pm_cfg.get("chain_id", 137)
        self._private_key: str = pm_cfg.get("wallet_private_key", "")
        self._api_key: str = pm_cfg.get("api_key", "")
        self._secret: str = pm_cfg.get("secret", "")

        self._http = httpx.Client(
            base_url=self.gamma_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

        self._clob: Optional[ClobClient] = None
        self._authenticated = False

    def connect(self) -> None:
        """Initialize CLOB client. Call once at startup."""
        if self._private_key:
            self._clob = ClobClient(
                self.base_url,
                key=self._private_key,
                chain_id=self.chain_id,
            )
            try:
                creds = self._clob.create_or_derive_api_creds()
                self._clob.set_api_creds(creds)
                self._authenticated = True
                logger.info("CLOB client authenticated (chain_id=%d)", self.chain_id)
            except Exception:
                logger.exception("Failed to authenticate CLOB client")
                self._authenticated = False
        else:
            self._clob = ClobClient(self.base_url)
            logger.info("CLOB client initialized (read-only, no private key)")

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    # ── Gamma API: Market Data ────────────────────────────────────────

    def get_events(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        order: str = "volume",
    ) -> list[dict[str, Any]]:
        """Fetch events from Gamma API with pagination."""
        params: dict[str, Any] = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
            "order": order,
        }
        resp = self._http.get("/events", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_event_by_slug(self, slug: str) -> Optional[dict[str, Any]]:
        """Fetch a single event by its slug."""
        resp = self._http.get("/events", params={"slug": slug})
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None

    def get_markets(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch markets from Gamma API with pagination."""
        params: dict[str, Any] = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }
        resp = self._http.get("/markets", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_all_active_events(self, max_pages: int = 10) -> list[dict[str, Any]]:
        """Paginate through all active events."""
        all_events: list[dict[str, Any]] = []
        for page in range(max_pages):
            batch = self.get_events(active=True, closed=False, limit=100, offset=page * 100)
            if not batch:
                break
            all_events.extend(batch)
            logger.debug("Fetched events page %d (%d events)", page, len(batch))
        logger.info("Total active events fetched: %d", len(all_events))
        return all_events

    # ── CLOB API: Orderbook & Prices ──────────────────────────────────

    def get_orderbook(self, token_id: str) -> dict[str, Any]:
        """Get orderbook for a token (YES or NO side)."""
        if not self._clob:
            raise RuntimeError("CLOB client not initialized — call connect() first")
        return self._clob.get_order_book(token_id)

    def get_price(self, token_id: str, side: str = "buy") -> Optional[float]:
        """Get best price for a token on given side."""
        if not self._clob:
            raise RuntimeError("CLOB client not initialized — call connect() first")
        try:
            price_str = self._clob.get_price(token_id, side)
            return float(price_str) if price_str else None
        except Exception:
            logger.warning("Failed to get price for token %s", token_id)
            return None

    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token."""
        if not self._clob:
            raise RuntimeError("CLOB client not initialized — call connect() first")
        try:
            mid = self._clob.get_midpoint(token_id)
            return float(mid) if mid else None
        except Exception:
            logger.warning("Failed to get midpoint for token %s", token_id)
            return None

    # ── CLOB API: Trading ─────────────────────────────────────────────

    def place_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        tick_size: str = "0.01",
        neg_risk: bool = False,
    ) -> dict[str, Any]:
        """Place a limit order. Side is 'buy' or 'sell'."""
        if not self._clob or not self._authenticated:
            raise RuntimeError("CLOB client not authenticated — cannot place orders")

        order_side = BUY if side.lower() == "buy" else SELL
        args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=order_side,
        )
        resp = self._clob.create_and_post_order(
            args,
            options={"tick_size": tick_size, "neg_risk": neg_risk},
            order_type=OrderType.GTC,
        )
        logger.info(
            "Order placed: %s %s @ %.4f x %.2f (token=%s)",
            side, "GTC", price, size, token_id[:16],
        )
        return resp

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel a specific order."""
        if not self._clob or not self._authenticated:
            raise RuntimeError("CLOB client not authenticated")
        return self._clob.cancel(order_id)

    def cancel_all_orders(self) -> dict[str, Any]:
        """Cancel all open orders."""
        if not self._clob or not self._authenticated:
            raise RuntimeError("CLOB client not authenticated")
        return self._clob.cancel_all()

    def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        if not self._clob or not self._authenticated:
            raise RuntimeError("CLOB client not authenticated")
        return self._clob.get_positions() or []

    # ── Lifecycle ─────────────────────────────────────────────────────

    def close(self) -> None:
        """Clean up HTTP connections."""
        self._http.close()
