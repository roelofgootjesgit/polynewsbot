"""Tests for market mapper."""
import uuid
from datetime import datetime, timezone

from src.models.events import NormalizedNewsEvent, SourceTier
from src.models.markets import MarketCandidate
from src.mapping.universe import MarketUniverse
from src.mapping.market_mapper import MarketMapper


def _make_cfg():
    return {
        "mapping": {
            "min_mapping_confidence": 0.3,
            "min_liquidity_score": 0.0,
            "max_markets_per_event": 3,
        },
        "filter": {"categories": ["crypto", "politics"]},
    }


def _make_event(headline, topics=None):
    return NormalizedNewsEvent(
        event_id=str(uuid.uuid4()),
        received_at=datetime.now(timezone.utc),
        source_name="Test",
        source_tier=SourceTier.TIER_2_TRUSTED_MEDIA,
        source_reliability_score=0.8,
        headline=headline,
        topic_hints=topics or [],
    )


def _make_universe_with_markets(cfg, markets):
    universe = MarketUniverse(cfg)
    universe._markets = markets
    return universe


def test_map_bitcoin_event():
    markets = [
        MarketCandidate(
            market_id="m1", condition_id="c1",
            market_title="Will Bitcoin reach $150,000 by December 2026?",
            resolution_text="Resolves YES if BTC exceeds $150k",
            liquidity_score=0.5, event_cluster_id="btc-150k",
        ),
        MarketCandidate(
            market_id="m2", condition_id="c2",
            market_title="Will Ethereum reach $10,000 by 2026?",
            resolution_text="Resolves YES if ETH exceeds $10k",
            liquidity_score=0.4,
        ),
    ]
    cfg = _make_cfg()
    universe = _make_universe_with_markets(cfg, markets)
    mapper = MarketMapper(cfg, universe)

    event = _make_event("Bitcoin surges past $120k in massive rally", topics=["crypto"])
    result = mapper.map_event(event)

    assert len(result.candidates) >= 1
    assert result.best is not None
    assert "bitcoin" in result.best.market_title.lower() or "btc" in result.best.market_title.lower()


def test_map_no_match():
    markets = [
        MarketCandidate(
            market_id="m1", condition_id="c1",
            market_title="Will it rain in Tokyo tomorrow?",
            resolution_text="Weather forecast based",
            liquidity_score=0.5,
        ),
    ]
    cfg = _make_cfg()
    universe = _make_universe_with_markets(cfg, markets)
    mapper = MarketMapper(cfg, universe)

    event = _make_event("Fed raises interest rates by 50bps", topics=["central_banks"])
    result = mapper.map_event(event)

    # Low confidence match or no match
    high_conf = [c for c in result.candidates if c[1] >= 0.6]
    assert len(high_conf) == 0


def test_max_candidates_respected():
    markets = [
        MarketCandidate(
            market_id=f"m{i}", condition_id=f"c{i}",
            market_title=f"Bitcoin price prediction market {i}",
            resolution_text="BTC related", liquidity_score=0.5,
        )
        for i in range(10)
    ]
    cfg = _make_cfg()
    universe = _make_universe_with_markets(cfg, markets)
    mapper = MarketMapper(cfg, universe)

    event = _make_event("Bitcoin breaks all time high", topics=["crypto"])
    result = mapper.map_event(event)
    assert len(result.candidates) <= 3
