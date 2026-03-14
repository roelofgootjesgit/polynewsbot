# Edge Engine — MODULE_CONTEXT

## Wat
Combineert model probability en market state tot een netto handelsbeslissing.

## Bestanden
- `engine.py` — EdgeEngine: ProbabilityAssessment + MarketState → TradeDecision

## Formules
- raw_edge = |model_probability - market_implied_probability|
- net_edge = raw_edge - fees - slippage - uncertainty_penalty
- uncertainty_penalty = (1 - confidence) * weight * raw_edge
- Side = YES als model > market, anders NO

## Minimum condities (alle config-driven)
- min_raw_edge (default 0.05)
- min_net_edge (default 0.03)

## Interfaces
- **Input:** ProbabilityAssessment + MarketState
- **Output:** TradeDecision (met execution_allowed flag)

## Config sectie: `edge.*` in default.yaml

## Status
- [x] Edge berekening + drempels — Fase 4 compleet
