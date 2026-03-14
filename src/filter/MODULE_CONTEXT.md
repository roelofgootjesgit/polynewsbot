# Relevance Filter — MODULE_CONTEXT

## Wat
Bepaalt of een NormalizedNewsEvent relevant is voor een verhandelbare prediction market.

## Bestanden
- `relevance.py` — RelevanceFilter + RelevanceResult

## RelevanceFilter
- `check(event)` → RelevanceResult (passed, score, semantic_score, time_score, reasons)
- `filter_batch(events)` → list van events die passeren

## Drie dimensies
1. **Semantic** (70% weight): topic overlap + keyword whitelist/blacklist + source tier boost
2. **Time** (30% weight): lineair verval van 1.0 (net gepubliceerd) naar 0.0 (max_age_minutes)
3. **Combined**: gewogen som, threshold via `min_relevance_score`

## Config sectie: `filter.*` in default.yaml

## Status
- [x] relevance.py — volledig werkend
- [x] Unit tests (8 passing)
