"""
Order manager — tracks order lifecycle, persists state, supports dry-run mode.
Adapted from OCLW bot OrderManager pattern.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_STATE_FILE = Path("data/orders_state.json")


class ManagedOrder(BaseModel):
    """An order being tracked by the order manager."""
    order_id: str
    internal_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_id: str = ""
    market_id: str = ""
    token_id: str = ""
    side: str = ""          # "buy" or "sell"
    price: float = 0.0
    size: float = 0.0
    filled: float = 0.0
    status: str = "pending"  # pending | open | partial | filled | cancelled | failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dry_run: bool = False
    response_data: Optional[dict] = None


class OrderManager:
    """Manages the lifecycle of orders with state persistence."""

    def __init__(self, cfg: dict[str, Any]):
        exec_cfg = cfg.get("execution", {})
        self.dry_run: bool = exec_cfg.get("dry_run", True)
        self.max_retry: int = exec_cfg.get("max_retry", 3)
        self._orders: dict[str, ManagedOrder] = {}

    def submit_order(
        self,
        client: Any,
        token_id: str,
        side: str,
        price: float,
        size: float,
        event_id: str = "",
        market_id: str = "",
    ) -> ManagedOrder:
        """Submit an order (or simulate in dry-run mode)."""
        order = ManagedOrder(
            order_id="",
            event_id=event_id,
            market_id=market_id,
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            dry_run=self.dry_run,
        )

        if self.dry_run:
            order.order_id = f"dry-{order.internal_id}"
            order.status = "filled"
            order.filled = size
            logger.info(
                "[DRY RUN] Order simulated: %s %s @ %.4f x %.2f (token=%s)",
                side, "GTC", price, size, token_id[:16],
            )
        else:
            try:
                from src.execution.polymarket_client import PolymarketClient
                assert isinstance(client, PolymarketClient)
                resp = client.place_order(
                    token_id=token_id,
                    side=side,
                    price=price,
                    size=size,
                )
                order.order_id = resp.get("orderID", resp.get("id", f"live-{order.internal_id}"))
                order.status = "open"
                order.response_data = resp
                logger.info("Order submitted: %s → %s", order.internal_id, order.order_id)
            except Exception:
                order.status = "failed"
                logger.exception("Order submission failed for %s", order.internal_id)

        order.updated_at = datetime.now(timezone.utc)
        self._orders[order.internal_id] = order
        self.save_state()
        return order

    def cancel(self, internal_id: str, client: Any = None) -> bool:
        """Cancel an order by internal ID."""
        order = self._orders.get(internal_id)
        if not order:
            logger.warning("Order %s not found", internal_id)
            return False

        if order.status in ("filled", "cancelled", "failed"):
            return False

        if not order.dry_run and client:
            try:
                from src.execution.polymarket_client import PolymarketClient
                assert isinstance(client, PolymarketClient)
                client.cancel_order(order.order_id)
            except Exception:
                logger.exception("Cancel failed for %s", order.order_id)
                return False

        order.status = "cancelled"
        order.updated_at = datetime.now(timezone.utc)
        self.save_state()
        logger.info("Order cancelled: %s (%s)", internal_id, order.order_id)
        return True

    def get_order(self, internal_id: str) -> Optional[ManagedOrder]:
        return self._orders.get(internal_id)

    def get_open_orders(self) -> list[ManagedOrder]:
        return [o for o in self._orders.values() if o.status in ("pending", "open", "partial")]

    def get_all_orders(self) -> list[ManagedOrder]:
        return list(self._orders.values())

    # ── State persistence ─────────────────────────────────────────────

    def save_state(self) -> None:
        """Persist current order state to disk."""
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.model_dump(mode="json") for k, v in self._orders.items()}
        _STATE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load_state(self) -> int:
        """Load order state from disk. Returns number of restored orders."""
        if not _STATE_FILE.exists():
            return 0
        try:
            raw = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            self._orders = {k: ManagedOrder.model_validate(v) for k, v in raw.items()}
            logger.info("Restored %d orders from state file", len(self._orders))
            return len(self._orders)
        except Exception:
            logger.exception("Failed to load order state")
            return 0
