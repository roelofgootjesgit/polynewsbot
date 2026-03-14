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
    """Run the bot (placeholder — Fase 5)."""
    cfg = load_config(args.config)
    setup_logging(cfg)
    logger.info("Polymarket News Bot starting...")
    logger.info("Mode: %s", "DRY RUN" if cfg.get("execution", {}).get("dry_run", True) else "LIVE")
    logger.warning("Pipeline not yet implemented — see DEVELOPMENT_PLAN.md Fase 5")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="newsbot",
        description="Polymarket News Trading Bot",
    )
    parser.add_argument("--config", "-c", default=None, help="Path to YAML config override")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show bot status and config").set_defaults(func=cmd_status)
    sub.add_parser("run", help="Run the bot pipeline").set_defaults(func=cmd_run)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception:
        logger.exception("Fatal error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
