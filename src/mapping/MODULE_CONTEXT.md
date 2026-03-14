# Market Mapping — MODULE_CONTEXT

## Wat
Koppelt relevant nieuws aan de juiste Polymarket markt(en).

## Bestanden
- `universe.py` — MarketUniverse: fetch, cache, filter, search active markets

## MarketUniverse
- `load_from_api(client)` — haalt alle active events op, parset naar MarketCandidate lijst
- `get_markets(category=None)` — gefilterd ophalen
- `find_by_id(market_id)` — zoek op condition_id of token_id
- `search(query)` — keyword search op titels
- `save_cache()` / `load_cache()` — disk persistence (data/market_universe_cache.json)

## Te bouwen (Fase 3)
- `market_mapper.py` — Twee-staps mapping: news topic → market cluster → specifieke markt

## Config sectie: `mapping.*` en `filter.categories` in default.yaml

## Status
- [x] universe.py — fetch + cache + filter + search
- [ ] market_mapper.py — gepland voor Fase 3
