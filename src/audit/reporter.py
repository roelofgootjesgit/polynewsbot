"""
Performance reporter — generates human-readable reports from
replay results and performance metrics.

Output modes:
  - Console (logger)
  - Markdown file (for sharing / review)
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.audit.performance import PerformanceMetrics
from src.audit.replay import ReplayResult

logger = logging.getLogger(__name__)


class PerformanceReporter:
    """Generates performance reports in multiple formats."""

    def console_replay_report(self, result: ReplayResult) -> str:
        """Print replay summary to console. Returns the formatted string."""
        lines = [
            "=" * 60,
            "REPLAY REPORT",
            "=" * 60,
            f"Total events:  {result.total_events}",
            f"  No match:    {result.no_match_events}",
            f"  Mapped:      {result.mapped_events}",
            f"  With edge:   {result.edge_events}",
            f"  Approved:    {result.approved_events}",
            f"  Vetoed:      {result.vetoed_events}",
            f"  Executed:    {result.executed_events}",
            "",
            f"Avg raw edge:  {result.avg_raw_edge:.4f}",
            f"Avg net edge:  {result.avg_net_edge:.4f}",
            f"Avg confidence:{result.avg_confidence:.4f}",
        ]

        if result.outcomes:
            lines.append("")
            lines.append("OUTCOMES:")
            for k, v in sorted(result.outcomes.items(), key=lambda x: -x[1]):
                lines.append(f"  {k}: {v}")

        if result.band_counts:
            lines.append("")
            lines.append("EDGE BANDS:")
            for k, v in sorted(result.band_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {k}: {v}")

        if result.veto_reason_counts:
            lines.append("")
            lines.append("VETO REASONS:")
            for k, v in sorted(result.veto_reason_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {k}: {v}")

        if result.source_stats:
            lines.append("")
            lines.append("SOURCE ATTRIBUTION:")
            for src, stats in sorted(result.source_stats.items()):
                lines.append(
                    f"  {src}: {stats['total']} events, "
                    f"{stats['approved']} approved, {stats['vetoed']} vetoed"
                )

        if result.method_counts:
            lines.append("")
            lines.append("PROBABILITY METHOD:")
            for k, v in sorted(result.method_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {k}: {v}")

        lines.append("=" * 60)
        report = "\n".join(lines)
        for line in lines:
            logger.info(line)
        return report

    def console_performance_report(self, metrics: PerformanceMetrics) -> str:
        """Print performance metrics to console."""
        lines = [
            "=" * 60,
            "PERFORMANCE REPORT",
            "=" * 60,
            f"Total trades:    {metrics.total_trades}",
            f"  Winning:       {metrics.winning_trades}",
            f"  Losing:        {metrics.losing_trades}",
            f"  Open:          {metrics.open_trades}",
            f"  Win rate:      {metrics.win_rate:.1%}",
            "",
            f"Total P&L:       ${metrics.total_pnl:.2f}",
            f"Avg P&L/trade:   ${metrics.avg_pnl:.4f}",
            f"Max win:         ${metrics.max_win:.2f}",
            f"Max loss:        ${metrics.max_loss:.2f}",
            "",
            f"Avg raw edge:    {metrics.avg_raw_edge:.4f}",
            f"Avg net edge:    {metrics.avg_net_edge:.4f}",
            f"Avg confidence:  {metrics.avg_confidence:.4f}",
            f"Avg hold time:   {metrics.avg_hold_minutes:.0f} min",
        ]

        if metrics.trades_by_band:
            lines.append("")
            lines.append("BY EDGE BAND:")
            for band in sorted(metrics.trades_by_band.keys()):
                n = metrics.trades_by_band[band]
                pnl = metrics.pnl_by_band.get(band, 0)
                wr = metrics.winrate_by_band.get(band, 0)
                lines.append(f"  {band}: {n} trades, ${pnl:.2f} P&L, {wr:.0%} win rate")

        if metrics.trades_by_source:
            lines.append("")
            lines.append("BY SOURCE:")
            for src in sorted(metrics.trades_by_source.keys()):
                n = metrics.trades_by_source[src]
                pnl = metrics.pnl_by_source.get(src, 0)
                lines.append(f"  {src}: {n} trades, ${pnl:.2f} P&L")

        if metrics.trades_by_method:
            lines.append("")
            lines.append("BY METHOD:")
            for method in sorted(metrics.trades_by_method.keys()):
                n = metrics.trades_by_method[method]
                pnl = metrics.pnl_by_method.get(method, 0)
                lines.append(f"  {method}: {n} trades, ${pnl:.2f} P&L")

        if metrics.exit_reason_counts:
            lines.append("")
            lines.append("EXIT REASONS:")
            for reason, count in sorted(metrics.exit_reason_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {reason}: {count}")

        lines.append("=" * 60)
        report = "\n".join(lines)
        for line in lines:
            logger.info(line)
        return report

    def markdown_report(
        self,
        replay: Optional[ReplayResult] = None,
        metrics: Optional[PerformanceMetrics] = None,
        output_path: str = "logs/performance_report.md",
    ) -> str:
        """Generate a markdown report and save to file."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"# Performance Report — {now}", ""]

        if replay:
            lines.extend(self._md_replay_section(replay))

        if metrics:
            lines.extend(self._md_performance_section(metrics))

        content = "\n".join(lines)

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Report saved to %s", path)

        return content

    def _md_replay_section(self, r: ReplayResult) -> list[str]:
        lines = [
            "## Decision Replay Summary", "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total events | {r.total_events} |",
            f"| No match | {r.no_match_events} |",
            f"| Mapped | {r.mapped_events} |",
            f"| Approved | {r.approved_events} |",
            f"| Vetoed | {r.vetoed_events} |",
            f"| Executed | {r.executed_events} |",
            f"| Avg raw edge | {r.avg_raw_edge:.4f} |",
            f"| Avg net edge | {r.avg_net_edge:.4f} |",
            f"| Avg confidence | {r.avg_confidence:.4f} |",
            "",
        ]

        if r.veto_reason_counts:
            lines.extend(["### Veto Reasons", "",
                          "| Reason | Count |", "|---|---|"])
            for k, v in sorted(r.veto_reason_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| {k} | {v} |")
            lines.append("")

        if r.band_counts:
            lines.extend(["### Edge Band Distribution", "",
                          "| Band | Count |", "|---|---|"])
            for k, v in sorted(r.band_counts.items(), key=lambda x: -x[1]):
                lines.append(f"| {k} | {v} |")
            lines.append("")

        if r.source_stats:
            lines.extend(["### Source Attribution", "",
                          "| Source | Total | Approved | Vetoed |", "|---|---|---|---|"])
            for src, stats in sorted(r.source_stats.items()):
                lines.append(f"| {src} | {stats['total']} | {stats['approved']} | {stats['vetoed']} |")
            lines.append("")

        return lines

    def _md_performance_section(self, m: PerformanceMetrics) -> list[str]:
        lines = [
            "## Trade Performance", "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total trades | {m.total_trades} |",
            f"| Win rate | {m.win_rate:.1%} |",
            f"| Total P&L | ${m.total_pnl:.2f} |",
            f"| Avg P&L/trade | ${m.avg_pnl:.4f} |",
            f"| Max win | ${m.max_win:.2f} |",
            f"| Max loss | ${m.max_loss:.2f} |",
            f"| Avg hold time | {m.avg_hold_minutes:.0f} min |",
            "",
        ]

        if m.trades_by_band:
            lines.extend(["### By Edge Band", "",
                          "| Band | Trades | P&L | Win Rate |", "|---|---|---|---|"])
            for band in sorted(m.trades_by_band.keys()):
                n = m.trades_by_band[band]
                pnl = m.pnl_by_band.get(band, 0)
                wr = m.winrate_by_band.get(band, 0)
                lines.append(f"| {band} | {n} | ${pnl:.2f} | {wr:.0%} |")
            lines.append("")

        return lines
