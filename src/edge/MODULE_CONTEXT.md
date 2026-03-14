# Edge Engine — MODULE_CONTEXT

## Wat
Combineert model probability en market state tot een netto handelsbeslissing.

## Te bouwen (Fase 4)
- `engine.py` — EdgeEngine: ProbabilityAssessment + MarketState → TradeDecision

## Formules
- raw_edge = model_probability - market_implied_probability
- net_edge = raw_edge - fees - slippage - uncertainty_penalty - execution_risk

## Minimum condities (alle config-driven)
- min_raw_edge, min_net_edge, min_confidence
- min_source_reliability, max_resolution_uncertainty
- min_orderbook_depth

## Interfaces
- **Input:** ProbabilityAssessment + MarketState
- **Output:** TradeDecision (met execution_allowed flag)

## Config sectie: `edge.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 4
