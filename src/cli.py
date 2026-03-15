"""
CLI entry point for the Polymarket News Bot.
"""
import argparse
import logging
import sys

from src.config import load_config, setup_logging

logger = logging.getLogger(__name__)


def cmd_status(args: argparse.Namespace) -> int:
    """Show bot status and config summary."""
    cfg = load_config(args.config)
    setup_logging(cfg)
    logger.info("Polymarket News Bot v0.1.0")
    logger.info("Mode: %s", "DRY RUN" if cfg.get("execution", {}).get("dry_run", True) else "LIVE")
    logger.info("Config loaded: %d sections", len(cfg))
    for section in sorted(cfg.keys()):
        logger.info("  [%s]", section)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run the bot pipeline."""
    cfg = load_config(args.config)
    setup_logging(cfg)

    from src.pipeline.orchestrator import EventPipeline

    mode = "DRY RUN" if cfg.get("execution", {}).get("dry_run", True) else "LIVE"
    logger.info("Polymarket News Bot starting... (%s)", mode)

    pipeline = EventPipeline(cfg)
    pipeline.setup()
    pipeline.run_loop(max_cycles=args.cycles)
    return 0


def cmd_cycle(args: argparse.Namespace) -> int:
    """Run a single pipeline cycle (useful for testing)."""
    cfg = load_config(args.config)
    setup_logging(cfg)

    from src.pipeline.orchestrator import EventPipeline

    logger.info("Running single pipeline cycle...")
    pipeline = EventPipeline(cfg)
    pipeline.setup()
    stats = pipeline.run_cycle()
    logger.info("Result: %s", stats.summary())
    pipeline.shutdown()
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Replay historical decision logs and show analysis."""
    cfg = load_config(args.config)
    setup_logging(cfg)

    from src.audit.replay import ReplayEngine
    from src.audit.reporter import PerformanceReporter

    log_dir = cfg.get("audit", {}).get("log_dir", "logs/decisions")
    engine = ReplayEngine(log_dir)
    result = engine.replay(date_from=args.date_from, date_to=args.date_to)

    reporter = PerformanceReporter()
    reporter.console_replay_report(result)

    if args.markdown:
        reporter.markdown_report(replay=result, output_path=args.markdown)

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate a markdown performance report."""
    cfg = load_config(args.config)
    setup_logging(cfg)

    from src.audit.replay import ReplayEngine
    from src.audit.reporter import PerformanceReporter

    log_dir = cfg.get("audit", {}).get("log_dir", "logs/decisions")
    engine = ReplayEngine(log_dir)
    result = engine.replay(date_from=args.date_from, date_to=args.date_to)

    reporter = PerformanceReporter()
    out = args.output or "logs/performance_report.md"
    reporter.markdown_report(replay=result, output_path=out)

    logger.info("Report written to %s", out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="newsbot",
        description="Polymarket News Trading Bot",
    )
    parser.add_argument("--config", "-c", default=None, help="Path to YAML config override")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show bot status and config").set_defaults(func=cmd_status)

    run_parser = sub.add_parser("run", help="Run the bot pipeline loop")
    run_parser.add_argument("--cycles", type=int, default=0, help="Max cycles (0=infinite)")
    run_parser.set_defaults(func=cmd_run)

    sub.add_parser("cycle", help="Run a single pipeline cycle").set_defaults(func=cmd_cycle)

    replay_parser = sub.add_parser("replay", help="Replay historical decision logs")
    replay_parser.add_argument("--date-from", default=None, help="Start date (YYYY-MM-DD)")
    replay_parser.add_argument("--date-to", default=None, help="End date (YYYY-MM-DD)")
    replay_parser.add_argument("--markdown", default=None, help="Also save markdown report to path")
    replay_parser.set_defaults(func=cmd_replay)

    report_parser = sub.add_parser("report", help="Generate markdown performance report")
    report_parser.add_argument("--date-from", default=None, help="Start date (YYYY-MM-DD)")
    report_parser.add_argument("--date-to", default=None, help="End date (YYYY-MM-DD)")
    report_parser.add_argument("--output", "-o", default=None, help="Output path (default: logs/performance_report.md)")
    report_parser.set_defaults(func=cmd_report)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception:
        logger.exception("Fatal error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
