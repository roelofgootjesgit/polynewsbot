"""
Integration tests — hits the real Polymarket Gamma API (read-only, no auth).
These tests require internet access. Skip with: pytest -m "not integration"
"""
import pytest

from src.config.loader import load_config
from src.execution.polymarket_client import PolymarketClient
from src.mapping.universe import MarketUniverse
from src.market_state.analyzer import MarketStateAnalyzer

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    cfg = load_config()
    c = PolymarketClient(cfg)
    c.connect()
    yield c
    c.close()


@pytest.fixture(scope="module")
def config():
    return load_config()


class TestGammaAPI:
    """Tests that hit the real Gamma API (public, no auth)."""

    def test_fetch_events(self, client):
        events = client.get_events(limit=5)
        assert isinstance(events, list)
        assert len(events) > 0
        event = events[0]
        assert "slug" in event or "title" in event

    def test_fetch_markets(self, client):
        markets = client.get_markets(limit=5)
        assert isinstance(markets, list)
        assert len(markets) > 0

    def test_event_contains_markets(self, client):
        events = client.get_events(limit=3)
        has_markets = any("markets" in e and len(e.get("markets", [])) > 0 for e in events)
        assert has_markets, "Expected at least one event with markets"


class TestMarketUniverse:
    """Tests universe loading from live API."""

    def test_load_universe(self, client, config):
        universe = MarketUniverse(config)
        count = universe.load_from_api(client)
        assert count > 0
        markets = universe.get_markets()
        assert len(markets) > 0
        assert all(m.market_title for m in markets)

    def test_search_markets(self, client, config):
        universe = MarketUniverse(config)
        universe.load_from_api(client)
        # There's almost always a bitcoin-related market on Polymarket
        results = universe.search("bitcoin")
        # Don't assert > 0 since market availability changes
        assert isinstance(results, list)


class TestOrderbook:
    """Tests that read an orderbook from CLOB (read-only)."""

    def test_get_orderbook_for_active_market(self, client, config):
        events = client.get_events(limit=20)
        ob = None
        used_token = None
        for event in events:
            for mkt in event.get("markets", []):
                tokens = mkt.get("clobTokenIds", [])
                if not tokens or not mkt.get("enableOrderBook"):
                    continue
                try:
                    ob = client.get_orderbook(tokens[0])
                    used_token = tokens[0]
                    break
                except Exception:
                    continue
            if ob is not None:
                break

        if ob is None or used_token is None:
            pytest.skip("No market with accessible orderbook found")

        assert isinstance(ob, dict)
        analyzer = MarketStateAnalyzer(config)
        state = analyzer.analyze(used_token[:16], ob)
        assert state.market_id == used_token[:16]
        if state.best_bid is not None:
            assert 0.0 <= state.best_bid <= 1.0
