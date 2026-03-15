"""
Performance tracker — accumulates trade-level and session-level metrics.
Tracks P&L, hit rate, edge accuracy, and per-source/per-band attribution.

Used both live (updated each cycle) and in replay mode.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TradeRecord(BaseModel):
    """A single completed trade for performance tracking."""
    trade_id: str = ""
    market_id: str = ""
    event_id: str = ""
    headline: str = ""
    source_name: str = ""
    source_tier: int = 0
    side: str = ""
    edge_band: str = ""
    method: str = ""

    entry_price: float = 0.0
    exit_price: Optional[float] = None
    size_usd: float = 0.0
    shares: float = 0.0

    model_prob: float = 0.0
    market_prob: float = 0.0
    raw_edge: float = 0.0
    net_edge: float = 0.0
    confidence: float = 0.0

    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    realized_pnl: float = 0.0
    hold_minutes: float = 0.0
    resolved: bool = False


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    open_trades: int = 0

    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0
    win_rate: float = 0.0

    avg_raw_edge: float = 0.0
    avg_net_edge: float = 0.0
    avg_confidence: float = 0.0
    avg_hold_minutes: float = 0.0

    pnl_by_band: dict[str, float] = Field(default_factory=dict)
    trades_by_band: dict[str, int] = Field(default_factory=dict)
    winrate_by_band: dict[str, float] = Field(default_factory=dict)

    pnl_by_source: dict[str, float] = Field(default_factory=dict)
    trades_by_source: dict[str, int] = Field(default_factory=dict)

    pnl_by_method: dict[str, float] = Field(default_factory=dict)
    trades_by_method: dict[str, int] = Field(default_factory=dict)

    exit_reason_counts: dict[str, int] = Field(default_factory=dict)


class PerformanceTracker:
    """Accumulates trade records and computes metrics."""

    def __init__(self):
        self._trades: list[TradeRecord] = []

    def record_trade(self, trade: TradeRecord) -> None:
        self._trades.append(trade)

    @property
    def trade_count(self) -> int:
        return len(self._trades)

    def compute_metrics(self, closed_only: bool = True) -> PerformanceMetrics:
        """Compute aggregate metrics from all recorded trades."""
        m = PerformanceMetrics()
        m.total_trades = len(self._trades)

        closed = [t for t in self._trades if t.exit_price is not None]
        m.open_trades = m.total_trades - len(closed)

        trades = closed if closed_only else self._trades
        if not trades:
            return m

        pnls = []
        raw_edges = []
        net_edges = []
        confs = []
        holds = []

        band_wins: dict[str, int] = {}
        band_total: dict[str, int] = {}
        source_wins: dict[str, int] = {}

        for t in trades:
            pnl = t.realized_pnl
            pnls.append(pnl)

            if pnl > 0:
                m.winning_trades += 1
            elif pnl < 0:
                m.losing_trades += 1

            m.max_win = max(m.max_win, pnl)
            m.max_loss = min(m.max_loss, pnl)

            raw_edges.append(t.raw_edge)
            net_edges.append(t.net_edge)
            confs.append(t.confidence)
            if t.hold_minutes > 0:
                holds.append(t.hold_minutes)

            # Per-band
            band = t.edge_band or "unknown"
            m.pnl_by_band[band] = m.pnl_by_band.get(band, 0) + pnl
            m.trades_by_band[band] = m.trades_by_band.get(band, 0) + 1
            band_total[band] = band_total.get(band, 0) + 1
            if pnl > 0:
                band_wins[band] = band_wins.get(band, 0) + 1

            # Per-source
            src = t.source_name or "unknown"
            m.pnl_by_source[src] = m.pnl_by_source.get(src, 0) + pnl
            m.trades_by_source[src] = m.trades_by_source.get(src, 0) + 1

            # Per-method
            method = t.method or "unknown"
            m.pnl_by_method[method] = m.pnl_by_method.get(method, 0) + pnl
            m.trades_by_method[method] = m.trades_by_method.get(method, 0) + 1

            # Exit reasons
            if t.exit_reason:
                m.exit_reason_counts[t.exit_reason] = m.exit_reason_counts.get(t.exit_reason, 0) + 1

        total_closed = len(trades)
        m.total_pnl = round(sum(pnls), 2)
        m.avg_pnl = round(m.total_pnl / total_closed, 4) if total_closed else 0
        m.win_rate = round(m.winning_trades / total_closed, 4) if total_closed else 0
        m.avg_raw_edge = round(sum(raw_edges) / len(raw_edges), 4) if raw_edges else 0
        m.avg_net_edge = round(sum(net_edges) / len(net_edges), 4) if net_edges else 0
        m.avg_confidence = round(sum(confs) / len(confs), 4) if confs else 0
        m.avg_hold_minutes = round(sum(holds) / len(holds), 1) if holds else 0

        for band, total in band_total.items():
            wins = band_wins.get(band, 0)
            m.winrate_by_band[band] = round(wins / total, 4) if total else 0

        return m

    def get_trades(self) -> list[TradeRecord]:
        return list(self._trades)
