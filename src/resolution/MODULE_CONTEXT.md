# Resolution Understanding — MODULE_CONTEXT

## Wat
Interpreteert de officiële marktresolutie als juridisch contract. Beschermt tegen te losse interpretaties.

## Te bouwen (Fase 3 rule-based, Fase 6 LLM)
- `parser.py` — Resolutietekst → gestructureerde criteria

## Interfaces
- **Input:** MarketCandidate.resolution_text + NormalizedNewsEvent
- **Output:** resolution match score, structured criteria

## Kernvragen die beantwoord moeten worden
- Wat moet er precies gebeuren voor YES?
- Welke bron bepaalt de uitkomst?
- Geldt een exacte deadline?
- Tellen voorlopige cijfers of alleen officiële bevestigingen?

## Hard rule: geen trade als resolution understanding onvoldoende zeker is

## Config sectie: `resolution.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 3/6
