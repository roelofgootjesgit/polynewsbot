"""
Exit engine — executes position exits based on monitor signals.
Handles the mechanics of closing a position (selling shares).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.execution.order_manager import OrderManager
from src.models.trades import Position
from src.monitor.position_monitor import PositionSnapshot, ThesisState
from src.risk.exposure import ExposureTracker

logger = logging.getLogger(__name__)


class ExitResult:
    """Result of an exit attempt."""
    __slots__ = ("executed", "position_id", "exit_signal", "exit_reason",
                 "realized_pnl", "order_id")

    def __init__(self):
        self.executed: bool = False
        self.position_id: str = ""
        self.exit_signal: str = ""
        self.exit_reason: str = ""
        self.realized_pnl: float = 0.0
        self.order_id: str = ""


class ExitEngine:
    """
    Processes exit signals from PositionMonitor and closes positions.
    Respects dry-run mode through OrderManager.
    """

    def __init__(self, cfg: dict[str, Any]):
        self._dry_run = cfg.get("execution", {}).get("dry_run", True)

    def process_exits(
        self,
        snapshots: list[PositionSnapshot],
        positions: dict[str, Position],
        order_manager: OrderManager,
        exposure: ExposureTracker,
        client: Any = None,
    ) -> list[ExitResult]:
        """Process all snapshots with exit signals. Returns list of exit results."""
        results = []
        for snap in snapshots:
            if not snap.exit_signal:
                continue

            pos = positions.get(snap.position_id)
            if not pos or pos.status != "open":
                continue

            result = self._close_position(
                pos, snap, order_manager, exposure, client
            )
            results.append(result)

        return results

    def _close_position(
        self,
        position: Position,
        snapshot: PositionSnapshot,
        order_manager: OrderManager,
        exposure: ExposureTracker,
        client: Any,
    ) -> ExitResult:
        """Execute the exit for a single position."""
        result = ExitResult()
        result.position_id = position.position_id
        result.exit_signal = snapshot.exit_signal or ""
        result.exit_reason = snapshot.exit_reason or ""

        sell_price = snapshot.current_price

        order = order_manager.submit_order(
            client=client,
            token_id=position.market_id,
            side="sell",
            price=round(sell_price, 2),
            size=round(position.shares, 2),
            event_id=position.event_id,
            market_id=position.market_id,
        )

        if order.status in ("filled", "open"):
            now = datetime.now(timezone.utc)
            position.exit_price = sell_price
            position.exit_timestamp = now
            position.exit_reason = snapshot.exit_reason
            position.status = "closed"
            position.realized_pnl = snapshot.unrealized_pnl_usd
            position.thesis_still_valid = (
                snapshot.thesis_state == ThesisState.VALID
            )

            exposure.remove_position(position.position_id)

            result.executed = True
            result.realized_pnl = snapshot.unrealized_pnl_usd
            result.order_id = order.order_id

            logger.info(
                "%s EXIT: %s %s @ %.4f | pnl=$%.2f | reason=%s | order=%s",
                "DRY" if order.dry_run else "LIVE",
                position.side, position.market_id[:16],
                sell_price, snapshot.unrealized_pnl_usd,
                snapshot.exit_signal, order.order_id,
            )
        else:
            logger.warning(
                "Exit order failed for %s: status=%s",
                position.position_id, order.status,
            )

        return result
