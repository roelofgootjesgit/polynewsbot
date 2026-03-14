"""
Pipeline orchestrator — connects all modules into one event-driven loop.

Flow per cycle:
  news_poll → relevance_filter → market_mapping → resolution_check
    → probability_update → market_state → edge_engine → guardrails → execution
"""
import logging
import time
from typing import Any, Optional

from src.audit.decision_logger import DecisionLogger, DecisionTrace
from src.edge.engine import EdgeEngine
from src.execution.order_manager import OrderManager
from src.execution.polymarket_client import PolymarketClient
from src.filter.relevance import RelevanceFilter
from src.mapping.market_mapper import MarketMapper
from src.mapping.universe import MarketUniverse
from src.market_state.analyzer import MarketStateAnalyzer
from src.models.events import NormalizedNewsEvent
from src.models.markets import MarketCandidate
from src.news.poller import NewsPoller
from src.probability.engine import ProbabilityEngine
from src.resolution.parser import ResolutionParser
from src.risk.exposure import ExposureTracker
from src.risk.guardrails import Guardrails

logger = logging.getLogger(__name__)


class PipelineStats:
    """Counters for a single pipeline cycle."""
    __slots__ = (
        "events_polled", "events_passed_filter", "markets_matched",
        "edges_found", "trades_approved", "trades_executed", "vetoed",
    )

    def __init__(self):
        self.events_polled = 0
        self.events_passed_filter = 0
        self.markets_matched = 0
        self.edges_found = 0
        self.trades_approved = 0
        self.trades_executed = 0
        self.vetoed = 0

    def summary(self) -> str:
        return (
            f"polled={self.events_polled} → filtered={self.events_passed_filter} "
            f"→ matched={self.markets_matched} → edges={self.edges_found} "
            f"→ approved={self.trades_approved} → executed={self.trades_executed} "
            f"(vetoed={self.vetoed})"
        )


class EventPipeline:
    """
    Main pipeline controller.
    Initializes all modules and runs the news→trade loop.
    """

    def __init__(self, cfg: dict[str, Any]):
        self._cfg = cfg
        self._capital: float = 10_000.0

        self.poller = NewsPoller(cfg)
        self.relevance = RelevanceFilter(cfg)
        self.universe = MarketUniverse(cfg)
        self.mapper = MarketMapper(cfg, self.universe)
        self.resolution = ResolutionParser(cfg)
        self.probability = ProbabilityEngine(cfg)
        self.state_analyzer = MarketStateAnalyzer(cfg)
        self.edge = EdgeEngine(cfg)
        self.guardrails = Guardrails(cfg)
        self.exposure = ExposureTracker()
        self.order_manager = OrderManager(cfg)
        self.decision_logger = DecisionLogger(cfg)

        self.client: Optional[PolymarketClient] = None
        self._running = False
        self._cycle_count = 0
        self._dry_run: bool = cfg.get("execution", {}).get("dry_run", True)

    def setup(self) -> None:
        """Initialize all connections and load data."""
        logger.info("=" * 60)
        logger.info("Pipeline setup — mode: %s", "DRY RUN" if self._dry_run else "LIVE")
        logger.info("=" * 60)

        self.client = PolymarketClient(self._cfg)
        self.client.connect()

        source_count = self.poller.setup()
        logger.info("News sources: %d", source_count)

        market_count = self.universe.load_from_api(self.client)
        if market_count == 0:
            market_count = self.universe.load_cache()
        else:
            self.universe.save_cache()
        logger.info("Market universe: %d markets", market_count)

        self.order_manager.load_state()
        logger.info("Pipeline ready")

    def run_loop(self, max_cycles: int = 0) -> None:
        """
        Main loop: poll → process → sleep → repeat.
        max_cycles=0 means infinite.
        """
        poll_interval = self._cfg.get("news", {}).get("poll_interval_seconds", 30)
        self._running = True

        logger.info("Starting pipeline loop (interval=%ds, max_cycles=%s)",
                     poll_interval, max_cycles or "∞")

        try:
            while self._running:
                self._cycle_count += 1

                if max_cycles and self._cycle_count > max_cycles:
                    logger.info("Max cycles reached (%d), stopping", max_cycles)
                    break

                stats = self.run_cycle()
                logger.info("Cycle %d: %s", self._cycle_count, stats.summary())

                self.decision_logger.flush()

                if self._running and (not max_cycles or self._cycle_count < max_cycles):
                    logger.debug("Sleeping %ds...", poll_interval)
                    time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Pipeline stopped by user")
        finally:
            self._running = False
            self.decision_logger.flush()
            self.shutdown()

    def run_cycle(self) -> PipelineStats:
        """Execute one full pipeline cycle."""
        stats = PipelineStats()

        # 1. Poll news
        events = self.poller.poll()
        stats.events_polled = len(events)
        if not events:
            return stats

        # 2. Relevance filter
        relevant = self.relevance.filter_batch(events)
        stats.events_passed_filter = len(relevant)
        if not relevant:
            return stats

        # 3. Process each event through the full pipeline
        for event in relevant:
            self._process_event(event, stats)

        return stats

    def _process_event(self, event: NormalizedNewsEvent, stats: PipelineStats) -> None:
        """Process a single news event through mapping → edge → execution."""
        trace = self.decision_logger.create_trace(event.event_id, event.headline)

        trace.add_step("event", {
            "source": event.source_name,
            "tier": event.source_tier.value,
            "headline": event.headline,
            "topics": event.topic_hints,
        })

        # 3a. Map to markets
        mapping = self.mapper.map_event(event)
        if not mapping.candidates:
            trace.set_outcome("no_match", "no markets mapped")
            return

        stats.markets_matched += len(mapping.candidates)
        trace.add_step("mapping", {
            "candidates": len(mapping.candidates),
            "best": mapping.best.market_title if mapping.best else None,
            "cluster": mapping.cluster_id,
        })

        # 3b. Evaluate each candidate
        for market, map_confidence in mapping.candidates:
            self._evaluate_candidate(event, market, map_confidence, mapping.cluster_id, stats, trace)

    def _evaluate_candidate(
        self,
        event: NormalizedNewsEvent,
        market: MarketCandidate,
        map_confidence: float,
        cluster_id: Optional[str],
        stats: PipelineStats,
        trace: DecisionTrace,
    ) -> None:
        """Evaluate one market candidate for a news event."""
        market_key = market.market_id[:16]

        # Resolution check
        criteria = self.resolution.parse_criteria(market)
        res_match = self.resolution.match_event(event, criteria)

        trace.add_step(f"resolution_{market_key}", {
            "type": criteria.resolution_type,
            "match_score": res_match.match_score,
            "matched_phrases": res_match.matched_phrases,
        })

        # Market state
        market_state = self._get_market_state(market)
        if not market_state:
            trace.add_step(f"market_state_{market_key}", {"error": "no orderbook"})
            return

        current_prob = market_state.implied_probability or 0.5

        trace.add_step(f"market_state_{market_key}", {
            "bid": market_state.best_bid,
            "ask": market_state.best_ask,
            "spread": market_state.spread,
            "implied_prob": current_prob,
            "liquidity": market_state.liquidity_quality,
        })

        # Probability assessment
        assessment = self.probability.assess(event, market, res_match, current_prob)

        trace.add_step(f"probability_{market_key}", {
            "model_prob": assessment.model_probability,
            "confidence": assessment.confidence_score,
            "direction": assessment.claim_direction,
            "method": assessment.method,
        })

        # Edge calculation
        decision = self.edge.evaluate(assessment, market_state)
        stats.edges_found += 1

        trace.add_step(f"edge_{market_key}", {
            "side": decision.side,
            "raw_edge": decision.raw_edge,
            "net_edge": decision.net_edge,
            "execution_allowed": decision.execution_allowed,
        })

        # Guardrails
        guardrail_result = self.guardrails.evaluate(
            decision=decision,
            assessment=assessment,
            market_state=market_state,
            exposure=self.exposure,
            capital=self._capital,
            cluster_id=cluster_id,
        )

        if guardrail_result.approved:
            stats.trades_approved += 1
            trace.add_step(f"guardrail_{market_key}", {
                "approved": True,
                "size_usd": guardrail_result.position_size_usd,
            })
            self._execute_trade(event, market, decision, guardrail_result.position_size_usd, stats, trace)
        else:
            stats.vetoed += 1
            trace.add_step(f"guardrail_{market_key}", {
                "approved": False,
                "reasons": guardrail_result.veto_reasons,
            })
            trace.set_outcome("vetoed", "; ".join(guardrail_result.veto_reasons))

    def _get_market_state(self, market: MarketCandidate):
        """Fetch orderbook and analyze market state. Returns None on failure."""
        if not self.client:
            return None
        try:
            orderbook = self.client.get_orderbook(market.market_id)
            return self.state_analyzer.analyze(market.market_id, orderbook)
        except Exception:
            logger.debug("No orderbook for %s", market.market_id[:16])
            return None

    def _execute_trade(
        self,
        event: NormalizedNewsEvent,
        market: MarketCandidate,
        decision,
        size_usd: float,
        stats: PipelineStats,
        trace: DecisionTrace,
    ) -> None:
        """Execute a trade (or simulate in dry-run)."""
        price = decision.market_probability
        if decision.side == "YES":
            price = min(decision.market_probability + 0.01, 0.99)
        else:
            price = max(1.0 - decision.market_probability + 0.01, 0.01)

        shares = size_usd / price if price > 0 else 0

        order = self.order_manager.submit_order(
            client=self.client,
            token_id=market.market_id,
            side="buy",
            price=round(price, 2),
            size=round(shares, 2),
            event_id=event.event_id,
            market_id=market.market_id,
        )

        stats.trades_executed += 1

        trace.add_step(f"execution_{market.market_id[:16]}", {
            "order_id": order.order_id,
            "side": decision.side,
            "price": price,
            "shares": shares,
            "size_usd": size_usd,
            "dry_run": order.dry_run,
            "status": order.status,
        })
        trace.set_outcome("executed" if not order.dry_run else "dry_run_executed",
                          f"{decision.side} @ {price:.4f} x {shares:.2f}")

        logger.info(
            "%s TRADE: %s %s @ %.4f x %.0f ($%.2f) | edge=%.4f | %s",
            "DRY" if order.dry_run else "LIVE",
            decision.side, market.market_title[:30],
            price, shares, size_usd, decision.net_edge,
            event.headline[:40],
        )

    def shutdown(self) -> None:
        """Clean up resources."""
        if self.client:
            self.client.close()
        self.order_manager.save_state()
        logger.info("Pipeline shutdown complete")

    def stop(self) -> None:
        """Signal the pipeline to stop after the current cycle."""
        self._running = False

    @property
    def cycle_count(self) -> int:
        return self._cycle_count
