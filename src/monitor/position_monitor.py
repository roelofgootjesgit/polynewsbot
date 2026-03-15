"""
Position monitor — tracks open positions for thesis validity,
repricing completion, and exit signals.

Core concept: prediction markets are thesis-driven. A position stays open
only as long as the original thesis holds. Exit triggers:
  1. Thesis invalidated by counter-news
  2. Repricing complete (edge absorbed by market)
  3. Time limit reached
  4. Manual kill switch
"""
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.models.trades import Position

logger = logging.getLogger(__name__)


class ThesisState(str, Enum):
    """State machine for position thesis validity."""
    VALID = "valid"
    WEAKENED = "weakened"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


class PositionSnapshot(BaseModel):
    """Point-in-time snapshot of a monitored position."""
    position_id: str
    market_id: str
    timestamp: datetime
    current_price: float
    entry_price: float
    side: str
    thesis_state: ThesisState = ThesisState.VALID
    repricing_pct: float = Field(0.0, description="How much of the edge has been absorbed (0-1)")
    unrealized_pnl_usd: float = 0.0
    unrealized_pnl_pct: float = 0.0
    hold_duration_minutes: float = 0.0
    exit_signal: Optional[str] = None
    exit_reason: Optional[str] = None


class MonitorConfig(BaseModel):
    check_interval_seconds: int = 60
    take_profit_edge_absorbed: float = 0.70
    force_exit_thesis_invalid: bool = True
    time_exit_hours: float = 72.0
    weakened_reduction_pct: float = 0.50
    repricing_window_minutes: float = 30.0


class PositionMonitor:
    """
    Monitors open positions and generates exit signals.
    Runs on each pipeline cycle to check all open positions.
    """

    def __init__(self, cfg: dict[str, Any]):
        mon_cfg = cfg.get("monitor", {})
        self.config = MonitorConfig(**{
            k: mon_cfg[k] for k in mon_cfg if k in MonitorConfig.model_fields
        })
        self._thesis_states: dict[str, ThesisState] = {}
        self._thesis_reasons: dict[str, str] = {}
        self._entry_model_probs: dict[str, float] = {}
        self._entry_edges: dict[str, float] = {}

    def register_position(
        self,
        position: Position,
        model_probability: float,
        net_edge: float,
    ) -> None:
        """Register a new position for monitoring."""
        self._thesis_states[position.position_id] = ThesisState.VALID
        self._thesis_reasons[position.position_id] = ""
        self._entry_model_probs[position.position_id] = model_probability
        self._entry_edges[position.position_id] = net_edge
        logger.info(
            "Monitoring position %s: %s %s @ %.4f, model_prob=%.4f, edge=%.4f",
            position.position_id, position.side, position.market_id[:16],
            position.entry_price, model_probability, net_edge,
        )

    def check_position(
        self,
        position: Position,
        current_price: float,
    ) -> PositionSnapshot:
        """
        Check a single position and return a snapshot with exit signals.
        Does NOT execute the exit — the pipeline decides.
        """
        now = datetime.now(timezone.utc)
        pid = position.position_id

        hold_minutes = (now - position.entry_timestamp).total_seconds() / 60.0
        thesis = self._thesis_states.get(pid, ThesisState.VALID)
        entry_edge = self._entry_edges.get(pid, 0.0)

        unrealized_pnl_usd, unrealized_pnl_pct = self._calc_pnl(
            position, current_price
        )
        repricing_pct = self._calc_repricing(
            position, current_price, entry_edge
        )

        exit_signal = None
        exit_reason = None

        # Check 1: Thesis invalidated
        if thesis == ThesisState.INVALIDATED and self.config.force_exit_thesis_invalid:
            exit_signal = "exit_thesis_invalid"
            exit_reason = self._thesis_reasons.get(pid, "thesis invalidated")

        # Check 2: Repricing complete (take profit)
        elif repricing_pct >= self.config.take_profit_edge_absorbed:
            exit_signal = "exit_repricing_complete"
            exit_reason = f"repricing {repricing_pct:.0%} >= {self.config.take_profit_edge_absorbed:.0%}"

        # Check 3: Time limit
        elif hold_minutes >= self.config.time_exit_hours * 60:
            exit_signal = "exit_time_limit"
            exit_reason = f"held {hold_minutes / 60:.1f}h >= {self.config.time_exit_hours}h limit"

        # Check 4: Thesis weakened — flag but don't auto-exit
        elif thesis == ThesisState.WEAKENED:
            exit_signal = None
            exit_reason = None

        snapshot = PositionSnapshot(
            position_id=pid,
            market_id=position.market_id,
            timestamp=now,
            current_price=current_price,
            entry_price=position.entry_price,
            side=position.side,
            thesis_state=thesis,
            repricing_pct=round(repricing_pct, 4),
            unrealized_pnl_usd=round(unrealized_pnl_usd, 4),
            unrealized_pnl_pct=round(unrealized_pnl_pct, 4),
            hold_duration_minutes=round(hold_minutes, 1),
            exit_signal=exit_signal,
            exit_reason=exit_reason,
        )

        if exit_signal:
            logger.info(
                "EXIT SIGNAL [%s]: %s %s | pnl=$%.2f (%.1f%%) | %s",
                exit_signal, position.side, position.market_id[:16],
                unrealized_pnl_usd, unrealized_pnl_pct * 100, exit_reason,
            )

        return snapshot

    def check_all(
        self,
        positions: list[Position],
        price_fetcher,
    ) -> list[PositionSnapshot]:
        """Check all open positions. price_fetcher(market_id) -> float or None."""
        snapshots = []
        for pos in positions:
            price = price_fetcher(pos.market_id)
            if price is None:
                continue
            snap = self.check_position(pos, price)
            snapshots.append(snap)
        return snapshots

    # --- Thesis Management ---

    def weaken_thesis(self, position_id: str, reason: str) -> None:
        """Downgrade thesis to weakened (e.g., conflicting but inconclusive news)."""
        current = self._thesis_states.get(position_id)
        if current == ThesisState.VALID:
            self._thesis_states[position_id] = ThesisState.WEAKENED
            self._thesis_reasons[position_id] = reason
            logger.info("Thesis WEAKENED for %s: %s", position_id, reason)

    def invalidate_thesis(self, position_id: str, reason: str) -> None:
        """Mark thesis as invalid (triggers exit if force_exit enabled)."""
        self._thesis_states[position_id] = ThesisState.INVALIDATED
        self._thesis_reasons[position_id] = reason
        logger.warning("Thesis INVALIDATED for %s: %s", position_id, reason)

    def get_thesis_state(self, position_id: str) -> ThesisState:
        return self._thesis_states.get(position_id, ThesisState.VALID)

    def remove_position(self, position_id: str) -> None:
        """Clean up state for a closed position."""
        self._thesis_states.pop(position_id, None)
        self._thesis_reasons.pop(position_id, None)
        self._entry_model_probs.pop(position_id, None)
        self._entry_edges.pop(position_id, None)

    # --- Internal Calculations ---

    def _calc_pnl(self, position: Position, current_price: float) -> tuple[float, float]:
        """Calculate unrealized P&L for a position."""
        if position.side == "YES":
            pnl_per_share = current_price - position.entry_price
        else:
            pnl_per_share = position.entry_price - current_price

        pnl_usd = pnl_per_share * position.shares
        pnl_pct = pnl_usd / position.cost_basis_usd if position.cost_basis_usd > 0 else 0.0
        return pnl_usd, pnl_pct

    def _calc_repricing(
        self, position: Position, current_price: float, entry_edge: float
    ) -> float:
        """
        How much of the original edge has the market absorbed?
        0.0 = no repricing, 1.0 = fully repriced to model probability.
        """
        if entry_edge <= 0:
            return 0.0

        entry_model_prob = self._entry_model_probs.get(position.position_id, 0.5)

        if position.side == "YES":
            price_move_toward_model = current_price - position.entry_price
            max_move = entry_model_prob - position.entry_price
        else:
            price_move_toward_model = position.entry_price - current_price
            max_move = position.entry_price - (1.0 - entry_model_prob)

        if max_move <= 0:
            return 0.0

        return min(max(price_move_toward_model / max_move, 0.0), 1.5)
