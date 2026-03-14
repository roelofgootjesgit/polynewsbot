# Relevance Filter — MODULE_CONTEXT

## Wat
Bepaalt of een NormalizedNewsEvent relevant is voor een verhandelbare prediction market.

## Te bouwen (Fase 3)
- `relevance.py` — RelevanceFilter: semantic, time, resolution relevance checks

## Interfaces
- **Input:** NormalizedNewsEvent (van news module)
- **Output:** NormalizedNewsEvent met relevance score, of gefilterd (dropped)

## Drie dimensies
1. Semantische relevantie — past topic bij market universe?
2. Tijdsrelevantie — is nieuws vers genoeg?
3. Resolutierelevantie — verandert dit werkelijk de kans op resolutie?

## Config sectie: `filter.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 3
