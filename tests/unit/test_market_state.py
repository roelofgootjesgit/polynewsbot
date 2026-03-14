"""Tests for market state analyzer."""
from src.market_state.analyzer import MarketStateAnalyzer, _estimate_slippage, _assess_quality
from src.models.markets import OrderBookLevel


def _make_cfg(**overrides):
    cfg = {"risk": {"max_spread": 0.10}}
    cfg["risk"].update(overrides)
    return cfg


def test_analyze_basic_orderbook():
    analyzer = MarketStateAnalyzer(_make_cfg())
    orderbook = {
        "bids": [
            {"price": "0.55", "size": "200"},
            {"price": "0.54", "size": "300"},
        ],
        "asks": [
            {"price": "0.58", "size": "150"},
            {"price": "0.59", "size": "250"},
        ],
    }
    state = analyzer.analyze("mkt-1", orderbook)
    assert state.market_id == "mkt-1"
    assert state.best_bid == 0.55
    assert state.best_ask == 0.58
    assert abs(state.spread - 0.03) < 1e-9
    assert abs(state.mid_price - 0.565) < 1e-9
    assert state.implied_probability == state.mid_price
    assert len(state.bid_depth) == 2
    assert len(state.ask_depth) == 2
    assert state.liquidity_quality in ("high", "medium", "low")


def test_analyze_empty_orderbook():
    analyzer = MarketStateAnalyzer(_make_cfg())
    state = analyzer.analyze("mkt-2", {"bids": [], "asks": []})
    assert state.best_bid is None
    assert state.best_ask is None
    assert state.spread is None
    assert state.liquidity_quality == "low"


def test_slippage_no_asks():
    assert _estimate_slippage([], 50.0) == 0.0


def test_slippage_single_level():
    asks = [OrderBookLevel(price=0.50, size=100.0)]
    assert _estimate_slippage(asks, 50.0) == 0.0


def test_slippage_multiple_levels():
    asks = [
        OrderBookLevel(price=0.50, size=20.0),
        OrderBookLevel(price=0.52, size=50.0),
    ]
    slippage = _estimate_slippage(asks, 50.0)
    assert slippage > 0


def test_quality_high():
    assert _assess_quality(0.02, 8000, 8000, 0.10) == "high"


def test_quality_low_spread():
    assert _assess_quality(0.15, 5000, 5000, 0.10) == "low"


def test_quality_low_liquidity():
    assert _assess_quality(0.03, 200, 200, 0.10) == "low"
