# Market Mapping — MODULE_CONTEXT

## Wat
Koppelt relevant nieuws aan de juiste Polymarket markt(en).

## Bestanden
- `universe.py` — MarketUniverse: fetch, cache, filter, search active markets
- `market_mapper.py` — MarketMapper: news event → ranked MarketCandidate list

## MarketMapper flow
1. Build search terms uit headline + topic_hints + key entities
2. Search universe op elke term
3. Score matches: keyword overlap + SequenceMatcher similarity + topic bonus + liquidity bonus
4. Dedup op condition_id, sort op confidence, cap op max_candidates

## MarketUniverse
- `load_from_api(client)` / `load_cache()` — markten ophalen
- `search(query)` — keyword search op titels
- `save_cache()` — disk persistence

## Config sectie: `mapping.*` in default.yaml

## Status
- [x] universe.py — fetch + cache + filter + search
- [x] market_mapper.py — two-step mapping met scoring
- [x] Unit tests (3 passing)
