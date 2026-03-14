# Market Mapping — MODULE_CONTEXT

## Wat
Koppelt relevant nieuws aan de juiste Polymarket markt(en).

## Te bouwen (Fase 3)
- `market_mapper.py` — Twee-staps mapping: topic cluster → specifieke markt
- `universe.py` — Market universe config en caching

## Interfaces
- **Input:** NormalizedNewsEvent (gefilterd)
- **Output:** list[MarketCandidate] met mapping_confidence

## Twee stappen
1. Event/topic cluster bepalen (bijv. "Fed", "Bitcoin ETF", "US Election")
2. Exacte marktselectie op deadline, resolutie, liquiditeit

## Config sectie: `mapping.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 3
