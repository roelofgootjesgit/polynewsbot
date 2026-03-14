# Market State Analyzer — MODULE_CONTEXT

## Wat
Beoordeelt of een markt praktisch verhandelbaar is. Leest orderboek en berekent metrics.

## Bestanden
- `analyzer.py` — MarketStateAnalyzer: orderbook dict → MarketState

## MarketStateAnalyzer
- `analyze(market_id, orderbook)` → MarketState
- Parseert bids/asks, berekent spread, mid price, implied probability
- Schat slippage in basis points
- Classificeert liquidity quality (high/medium/low)

## Interfaces
- **Input:** market_id + raw orderbook dict (van PolymarketClient.get_orderbook())
- **Output:** MarketState (Pydantic model uit src.models.markets)

## Config: gebruikt `risk.max_spread` voor quality assessment

## Status
- [x] analyzer.py — volledig werkend
- [x] Unit tests (8 passing)
