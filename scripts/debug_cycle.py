"""
Debug script: run one pipeline cycle with verbose output.
Shows exactly what happens at each step.
"""
import logging
import sys

sys.path.insert(0, ".")

from src.config import load_config, setup_logging
from src.execution.polymarket_client import PolymarketClient
from src.filter.relevance import RelevanceFilter
from src.mapping.market_mapper import MarketMapper
from src.mapping.universe import MarketUniverse
from src.news.poller import NewsPoller

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("debug")

cfg = load_config()
log.info("min_mapping_confidence: %s", cfg.get("mapping", {}).get("min_mapping_confidence"))
log.info("min_liquidity_score: %s", cfg.get("mapping", {}).get("min_liquidity_score"))

log.info("\n=== 1. News poll ===")
poller = NewsPoller(cfg)
poller.setup()
events = poller.poll()
log.info("Got %d events", len(events))

log.info("\n=== 2. Relevance filter ===")
filt = RelevanceFilter(cfg)
passed = filt.filter_batch(events)
log.info("%d/%d passed", len(passed), len(events))

log.info("\n=== 3. Market universe ===")
client = PolymarketClient(cfg)
client.connect()
universe = MarketUniverse(cfg)
count = universe.load_cache()
if count == 0:
    count = universe.load_from_api(client)
log.info("%d markets loaded", count)

log.info("\n=== 4. Detailed mapping debug ===")
mapper = MarketMapper(cfg, universe)

for e in passed[:8]:
    terms = mapper._build_search_terms(e)
    log.info("\nEvent: '%s'", e.headline[:70])
    log.info("  Topics: %s | Terms: %s", e.topic_hints, terms[:5])

    for term in terms[:3]:
        found = universe.search(term)
        if found:
            for m in found[:3]:
                score = mapper._score_match(e, m, term)
                log.info(
                    "  term='%s' -> score=%.3f, liq=%.3f | '%s'",
                    term, score, m.liquidity_score, m.market_title[:55]
                )

client.close()
