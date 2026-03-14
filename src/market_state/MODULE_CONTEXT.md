# Market State Analyzer — MODULE_CONTEXT

## Wat
Beoordeelt of een markt praktisch verhandelbaar is. Leest orderboek, spread, liquiditeit.

## Te bouwen (Fase 1)
- `analyzer.py` — MarketStateAnalyzer: market_id → MarketState

## Interfaces
- **Input:** market_id (via Polymarket adapter)
- **Output:** MarketState (bid/ask, spread, depth, slippage estimate, liquidity quality)

## Key insight
Theoretische edge is waardeloos als execution de volledige edge opeet.

## Config sectie: gebruikt `edge.*` en `risk.*` thresholds

## Status
- [ ] Niet gestart — gepland voor Fase 1
