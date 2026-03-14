"""
Exposure tracker — tracks portfolio exposure per event cluster and total.
"""
import logging
from typing import Optional

from src.models.trades import Position

logger = logging.getLogger(__name__)


class ExposureTracker:
    """Tracks capital at risk across positions and event clusters."""

    def __init__(self):
        self._positions: dict[str, Position] = {}

    def add_position(self, position: Position) -> None:
        self._positions[position.position_id] = position

    def remove_position(self, position_id: str) -> None:
        self._positions.pop(position_id, None)

    def get_cluster_exposure(self, cluster_id: Optional[str]) -> float:
        """Total USD exposure for an event cluster."""
        if not cluster_id:
            return 0.0
        return sum(
            p.cost_basis_usd
            for p in self._positions.values()
            if p.status == "open" and self._get_cluster(p) == cluster_id
        )

    def get_total_exposure(self) -> float:
        """Total USD exposure across all open positions."""
        return sum(
            p.cost_basis_usd
            for p in self._positions.values()
            if p.status == "open"
        )

    def get_open_positions(self) -> list[Position]:
        return [p for p in self._positions.values() if p.status == "open"]

    def get_position_count(self) -> int:
        return len([p for p in self._positions.values() if p.status == "open"])

    def _get_cluster(self, position: Position) -> Optional[str]:
        """Derive cluster from position. Stored in event_id for now."""
        return getattr(position, "_cluster_id", None)

    def set_cluster(self, position_id: str, cluster_id: str) -> None:
        """Associate a position with an event cluster."""
        pos = self._positions.get(position_id)
        if pos:
            pos._cluster_id = cluster_id  # type: ignore[attr-defined]
