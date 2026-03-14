# Models — MODULE_CONTEXT

## Wat
Gedeelde Pydantic data models. De enige bron van waarheid voor data contracts tussen modules.

## Bestanden
- `events.py` — NormalizedNewsEvent, RawNewsItem, SourceTier
- `markets.py` — MarketCandidate, MarketState, OrderBookLevel
- `probability.py` — ProbabilityAssessment
- `trades.py` — TradeDecision, Position

## Regels
- Elke module importeert modellen ALLEEN uit `src.models`
- Wijzigingen hier raken alle downstream modules — wees voorzichtig
- Validatie zit in de modellen (Pydantic), niet in de modules zelf

## Status
- [x] NormalizedNewsEvent + SourceTier + RawNewsItem
- [x] MarketCandidate + MarketState + OrderBookLevel
- [x] ProbabilityAssessment
- [x] TradeDecision + Position
