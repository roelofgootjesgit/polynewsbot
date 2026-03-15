"""Tests for audit: replay engine, performance tracker, and reporter."""
import json
import tempfile
from pathlib import Path

from src.audit.performance import PerformanceMetrics, PerformanceTracker, TradeRecord
from src.audit.replay import ReplayEngine, ReplayEvent, ReplayResult
from src.audit.reporter import PerformanceReporter


def _sample_log_entry(
    event_id="evt-1",
    headline="Fed approves rate cut",
    outcome="dry_run_executed",
    source="Reuters",
    tier=2,
    model_prob=0.65,
    confidence=0.8,
    raw_edge=0.10,
    net_edge=0.06,
    side="YES",
    edge_band="strong",
    approved=True,
    method="rule_based",
):
    return {
        "event_id": event_id,
        "headline": headline,
        "timestamp": "2026-03-14T22:00:00+00:00",
        "outcome": outcome,
        "final_reason": f"{side} @ 0.56",
        "steps": {
            "event": {"source": source, "tier": tier, "headline": headline},
            "mapping": {"candidates": 1, "best": "Fed rate cut?"},
            f"probability_{event_id[:8]}": {
                "model_prob": model_prob,
                "confidence": confidence,
                "direction": "positive",
                "method": method,
            },
            f"edge_{event_id[:8]}": {
                "side": side,
                "raw_edge": raw_edge,
                "net_edge": net_edge,
                "execution_allowed": True,
                "edge_band": edge_band,
            },
            f"guardrail_{event_id[:8]}": {
                "approved": approved,
                "size_usd": 50.0,
                "reasons": [] if approved else ["confidence too low"],
            },
        },
    }


# --- Replay Engine ---

class TestReplayEngine:
    def test_load_from_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "decisions_2026-03-14.jsonl"
            entries = [_sample_log_entry(event_id=f"evt-{i}") for i in range(3)]
            log_file.write_text(
                "\n".join(json.dumps(e) for e in entries),
                encoding="utf-8",
            )

            engine = ReplayEngine(tmpdir)
            events = engine.load_events()
            assert len(events) == 3
            assert events[0].source_name == "Reuters"
            assert events[0].raw_edge == 0.10

    def test_load_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ReplayEngine(tmpdir)
            events = engine.load_events()
            assert len(events) == 0

    def test_date_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for date in ["2026-03-12", "2026-03-13", "2026-03-14"]:
                f = Path(tmpdir) / f"decisions_{date}.jsonl"
                f.write_text(
                    json.dumps(_sample_log_entry(event_id=f"evt-{date}")),
                    encoding="utf-8",
                )

            engine = ReplayEngine(tmpdir)
            events = engine.load_events(date_from="2026-03-13", date_to="2026-03-13")
            assert len(events) == 1

    def test_replay_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "decisions_2026-03-14.jsonl"
            entries = [
                _sample_log_entry(event_id="evt-1", outcome="dry_run_executed", approved=True),
                _sample_log_entry(event_id="evt-2", outcome="vetoed", approved=False),
                _sample_log_entry(event_id="evt-3", outcome="no_match"),
            ]
            log_file.write_text(
                "\n".join(json.dumps(e) for e in entries),
                encoding="utf-8",
            )

            engine = ReplayEngine(tmpdir)
            result = engine.replay()
            assert result.total_events == 3
            assert result.executed_events == 1
            assert result.vetoed_events == 1
            assert result.no_match_events == 1

    def test_enrich_extracts_fields(self):
        engine = ReplayEngine("nonexistent")
        raw = _sample_log_entry(
            source="CoinDesk", tier=2,
            model_prob=0.72, raw_edge=0.12,
            edge_band="strong", method="llm",
        )
        ev = engine._enrich(raw)
        assert ev.source_name == "CoinDesk"
        assert ev.source_tier == 2
        assert ev.model_prob == 0.72
        assert ev.raw_edge == 0.12
        assert ev.edge_band == "strong"
        assert ev.method == "llm"


# --- Performance Tracker ---

class TestPerformanceTracker:
    def _make_trade(self, pnl=5.0, **kw) -> TradeRecord:
        defaults = dict(
            trade_id="t-1", market_id="mkt-1", event_id="evt-1",
            side="YES", edge_band="normal", method="rule_based",
            source_name="Reuters", source_tier=2,
            entry_price=0.55, exit_price=0.60, size_usd=50.0,
            shares=90.0, model_prob=0.65, market_prob=0.55,
            raw_edge=0.10, net_edge=0.06, confidence=0.8,
            realized_pnl=pnl, hold_minutes=30.0,
            exit_reason="exit_repricing_complete",
        )
        defaults.update(kw)
        return TradeRecord(**defaults)

    def test_empty_tracker(self):
        tracker = PerformanceTracker()
        m = tracker.compute_metrics()
        assert m.total_trades == 0
        assert m.win_rate == 0

    def test_single_winning_trade(self):
        tracker = PerformanceTracker()
        tracker.record_trade(self._make_trade(pnl=10.0))
        m = tracker.compute_metrics()
        assert m.total_trades == 1
        assert m.winning_trades == 1
        assert m.win_rate == 1.0
        assert m.total_pnl == 10.0

    def test_mixed_trades(self):
        tracker = PerformanceTracker()
        tracker.record_trade(self._make_trade(trade_id="t-1", pnl=15.0))
        tracker.record_trade(self._make_trade(trade_id="t-2", pnl=-5.0))
        tracker.record_trade(self._make_trade(trade_id="t-3", pnl=8.0))
        m = tracker.compute_metrics()
        assert m.total_trades == 3
        assert m.winning_trades == 2
        assert m.losing_trades == 1
        assert m.total_pnl == 18.0
        assert abs(m.win_rate - 2 / 3) < 0.001

    def test_per_band_attribution(self):
        tracker = PerformanceTracker()
        tracker.record_trade(self._make_trade(trade_id="t-1", pnl=10, edge_band="strong"))
        tracker.record_trade(self._make_trade(trade_id="t-2", pnl=-3, edge_band="normal"))
        m = tracker.compute_metrics()
        assert m.pnl_by_band["strong"] == 10
        assert m.pnl_by_band["normal"] == -3
        assert m.winrate_by_band["strong"] == 1.0
        assert m.winrate_by_band["normal"] == 0.0

    def test_per_source_attribution(self):
        tracker = PerformanceTracker()
        tracker.record_trade(self._make_trade(trade_id="t-1", pnl=5, source_name="Reuters"))
        tracker.record_trade(self._make_trade(trade_id="t-2", pnl=3, source_name="CoinDesk"))
        m = tracker.compute_metrics()
        assert m.pnl_by_source["Reuters"] == 5
        assert m.pnl_by_source["CoinDesk"] == 3

    def test_open_trade_excluded_from_closed_metrics(self):
        tracker = PerformanceTracker()
        tracker.record_trade(self._make_trade(pnl=10.0))
        tracker.record_trade(TradeRecord(
            trade_id="t-open", side="YES", entry_price=0.50,
            exit_price=None, realized_pnl=0,
        ))
        m = tracker.compute_metrics(closed_only=True)
        assert m.total_trades == 2
        assert m.open_trades == 1
        assert m.winning_trades == 1


# --- Reporter ---

class TestReporter:
    def test_console_replay_report(self):
        result = ReplayResult(
            total_events=10, no_match_events=3, mapped_events=7,
            edge_events=5, approved_events=2, vetoed_events=3,
            executed_events=2, avg_raw_edge=0.08, avg_net_edge=0.04,
            avg_confidence=0.7,
            outcomes={"dry_run_executed": 2, "vetoed": 3, "no_match": 5},
        )
        reporter = PerformanceReporter()
        text = reporter.console_replay_report(result)
        assert "REPLAY REPORT" in text
        assert "10" in text

    def test_console_performance_report(self):
        metrics = PerformanceMetrics(
            total_trades=5, winning_trades=3, losing_trades=2,
            total_pnl=25.5, win_rate=0.6,
        )
        reporter = PerformanceReporter()
        text = reporter.console_performance_report(metrics)
        assert "PERFORMANCE REPORT" in text
        assert "25.5" in text

    def test_markdown_report_saved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "report.md"
            replay = ReplayResult(total_events=5, approved_events=2, vetoed_events=3)
            metrics = PerformanceMetrics(total_trades=3, win_rate=0.67, total_pnl=12.0)

            reporter = PerformanceReporter()
            content = reporter.markdown_report(
                replay=replay, metrics=metrics, output_path=str(out_path),
            )
            assert out_path.exists()
            assert "# Performance Report" in content
            assert "Decision Replay" in content
            assert "Trade Performance" in content
