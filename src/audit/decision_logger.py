"""
Decision logger — logs every pipeline step for full audit trail.
Each news event that enters the pipeline gets a decision trace.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DecisionTrace:
    """Accumulates a full decision trace for one news event through the pipeline."""

    def __init__(self, event_id: str, headline: str):
        self.event_id = event_id
        self.headline = headline
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.steps: dict[str, Any] = {}
        self.outcome: str = "pending"
        self.final_reason: str = ""

    def add_step(self, step: str, data: dict[str, Any]) -> None:
        self.steps[step] = data

    def set_outcome(self, outcome: str, reason: str = "") -> None:
        self.outcome = outcome
        self.final_reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "headline": self.headline,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
            "final_reason": self.final_reason,
            "steps": self.steps,
        }


class DecisionLogger:
    """Persists decision traces to disk as JSON-lines."""

    def __init__(self, cfg: dict[str, Any]):
        audit_cfg = cfg.get("audit", {})
        self.enabled: bool = audit_cfg.get("log_decisions", True)
        self.log_dir = Path(audit_cfg.get("log_dir", "logs/decisions"))
        self._traces: list[DecisionTrace] = []

    def create_trace(self, event_id: str, headline: str) -> DecisionTrace:
        trace = DecisionTrace(event_id, headline)
        self._traces.append(trace)
        return trace

    def flush(self) -> int:
        """Write pending traces to disk. Returns count written."""
        if not self.enabled or not self._traces:
            return 0

        self.log_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filepath = self.log_dir / f"decisions_{date_str}.jsonl"

        count = 0
        with open(filepath, "a", encoding="utf-8") as f:
            for trace in self._traces:
                f.write(json.dumps(trace.to_dict(), default=str) + "\n")
                count += 1

        logger.info("Flushed %d decision traces -> %s", count, filepath)
        self._traces.clear()
        return count

    @property
    def pending_count(self) -> int:
        return len(self._traces)
