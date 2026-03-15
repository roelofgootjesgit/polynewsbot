"""
Replay engine — loads historical decision logs and replays them
for counterfactual analysis and performance measurement.

No future leakage: events are processed in chronological order,
and each decision is evaluated with only the information available at that time.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReplayEvent(BaseModel):
    """A single event from a decision log, enriched for replay analysis."""
    event_id: str
    headline: str
    timestamp: str
    outcome: str
    final_reason: str = ""
    steps: dict[str, Any] = Field(default_factory=dict)

    # Extracted fields for analysis (populated by _enrich)
    source_name: Optional[str] = None
    source_tier: Optional[int] = None
    market_id: Optional[str] = None
    market_title: Optional[str] = None
    model_prob: Optional[float] = None
    market_prob: Optional[float] = None
    confidence: Optional[float] = None
    raw_edge: Optional[float] = None
    net_edge: Optional[float] = None
    edge_band: Optional[str] = None
    side: Optional[str] = None
    size_usd: Optional[float] = None
    approved: Optional[bool] = None
    veto_reasons: list[str] = Field(default_factory=list)
    method: Optional[str] = None


class ReplayResult(BaseModel):
    """Aggregated result of a replay run."""
    total_events: int = 0
    filtered_events: int = 0
    mapped_events: int = 0
    edge_events: int = 0
    approved_events: int = 0
    vetoed_events: int = 0
    executed_events: int = 0
    no_match_events: int = 0

    outcomes: dict[str, int] = Field(default_factory=dict)
    veto_reason_counts: dict[str, int] = Field(default_factory=dict)
    band_counts: dict[str, int] = Field(default_factory=dict)

    source_stats: dict[str, dict[str, int]] = Field(default_factory=dict)
    method_counts: dict[str, int] = Field(default_factory=dict)

    avg_raw_edge: float = 0.0
    avg_net_edge: float = 0.0
    avg_confidence: float = 0.0

    events: list[ReplayEvent] = Field(default_factory=list)


class ReplayEngine:
    """Loads and replays historical decision logs."""

    def __init__(self, log_dir: str = "logs/decisions"):
        self._log_dir = Path(log_dir)

    def load_events(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 0,
    ) -> list[ReplayEvent]:
        """Load events from JSONL decision logs."""
        events = []
        for raw in self._read_logs(date_from, date_to):
            try:
                enriched = self._enrich(raw)
                events.append(enriched)
            except Exception as e:
                logger.debug("Skip malformed log entry: %s", str(e)[:80])

        events.sort(key=lambda e: e.timestamp)

        if limit > 0:
            events = events[:limit]

        logger.info("Loaded %d replay events from %s", len(events), self._log_dir)
        return events

    def replay(
        self,
        events: Optional[list[ReplayEvent]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> ReplayResult:
        """Replay events and compute aggregate statistics."""
        if events is None:
            events = self.load_events(date_from, date_to)

        result = ReplayResult(events=events)
        raw_edges = []
        net_edges = []
        confidences = []

        for ev in events:
            result.total_events += 1

            outcome = ev.outcome
            result.outcomes[outcome] = result.outcomes.get(outcome, 0) + 1

            if outcome == "no_match":
                result.no_match_events += 1
                continue

            result.mapped_events += 1

            if ev.raw_edge is not None:
                result.edge_events += 1
                raw_edges.append(ev.raw_edge)
                if ev.net_edge is not None:
                    net_edges.append(ev.net_edge)
                if ev.confidence is not None:
                    confidences.append(ev.confidence)

            if ev.edge_band:
                result.band_counts[ev.edge_band] = result.band_counts.get(ev.edge_band, 0) + 1

            if ev.approved is True:
                result.approved_events += 1
            elif ev.approved is False:
                result.vetoed_events += 1
                for reason in ev.veto_reasons:
                    short = reason.split(":")[0].strip() if ":" in reason else reason[:40]
                    result.veto_reason_counts[short] = result.veto_reason_counts.get(short, 0) + 1

            if "executed" in outcome or "dry_run" in outcome:
                result.executed_events += 1

            # Source stats
            src = ev.source_name or "unknown"
            if src not in result.source_stats:
                result.source_stats[src] = {"total": 0, "approved": 0, "vetoed": 0}
            result.source_stats[src]["total"] += 1
            if ev.approved:
                result.source_stats[src]["approved"] += 1
            elif ev.approved is False:
                result.source_stats[src]["vetoed"] += 1

            # Method stats
            if ev.method:
                result.method_counts[ev.method] = result.method_counts.get(ev.method, 0) + 1

        if raw_edges:
            result.avg_raw_edge = round(sum(raw_edges) / len(raw_edges), 4)
        if net_edges:
            result.avg_net_edge = round(sum(net_edges) / len(net_edges), 4)
        if confidences:
            result.avg_confidence = round(sum(confidences) / len(confidences), 4)

        return result

    def _read_logs(
        self, date_from: Optional[str], date_to: Optional[str]
    ) -> Iterator[dict[str, Any]]:
        """Read JSONL log files, optionally filtered by date range."""
        if not self._log_dir.exists():
            logger.warning("Log directory not found: %s", self._log_dir)
            return

        for f in sorted(self._log_dir.glob("decisions_*.jsonl")):
            file_date = f.stem.replace("decisions_", "")
            if date_from and file_date < date_from:
                continue
            if date_to and file_date > date_to:
                continue

            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def _enrich(self, raw: dict[str, Any]) -> ReplayEvent:
        """Extract analysis-relevant fields from a raw decision log entry."""
        steps = raw.get("steps", {})
        event_step = steps.get("event", {})

        # Find first probability/edge/guardrail step
        prob_data = {}
        edge_data = {}
        guard_data = {}
        exec_data = {}
        for key, val in steps.items():
            if key.startswith("probability_") and not prob_data:
                prob_data = val
            elif key.startswith("edge_") and not edge_data:
                edge_data = val
            elif key.startswith("guardrail_") and not guard_data:
                guard_data = val
            elif key.startswith("execution_") and not exec_data:
                exec_data = val

        return ReplayEvent(
            event_id=raw.get("event_id", ""),
            headline=raw.get("headline", ""),
            timestamp=raw.get("timestamp", ""),
            outcome=raw.get("outcome", "unknown"),
            final_reason=raw.get("final_reason", ""),
            steps=steps,
            source_name=event_step.get("source"),
            source_tier=event_step.get("tier"),
            model_prob=prob_data.get("model_prob"),
            market_prob=edge_data.get("market_probability") if edge_data else None,
            confidence=prob_data.get("confidence"),
            raw_edge=edge_data.get("raw_edge"),
            net_edge=edge_data.get("net_edge"),
            edge_band=edge_data.get("edge_band") or exec_data.get("edge_band"),
            side=edge_data.get("side"),
            size_usd=guard_data.get("size_usd") or exec_data.get("size_usd"),
            approved=guard_data.get("approved"),
            veto_reasons=guard_data.get("reasons", []) if isinstance(guard_data.get("reasons"), list) else [],
            method=prob_data.get("method"),
        )
