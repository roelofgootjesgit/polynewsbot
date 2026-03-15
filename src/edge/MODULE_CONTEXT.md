# Edge Engine — MODULE_CONTEXT

## Wat
Combineert model probability en market state tot een netto handelsbeslissing.
Classificeert edge in banden (strong/normal/observe) per quant review.

## Bestanden
- `engine.py` — EdgeEngine met EdgeBand classificatie

## Formules
- raw_edge = |model_probability - market_implied_probability|
- net_edge = raw_edge - fees - slippage - uncertainty_penalty
- uncertainty_penalty = (1 - confidence) * weight * raw_edge
- Side = YES als model > market, anders NO

## Edge Banden (configurable)
| Band | Raw Edge | Net Edge | Actie |
|---|---|---|---|
| strong | >= 8% | >= 5% | Full size trade (scale=1.0) |
| normal | >= 5% | >= 3% | Reduced size trade (scale=0.7) |
| observe | >= 3% | >= 0% | Log-only, niet traden |

## Interfaces
- **Input:** ProbabilityAssessment + MarketState
- **Output:** TradeDecision (met edge_band + size_scale)

## Config sectie: `edge.*` in default.yaml

## Status
- [x] Edge berekening + drempels — Fase 4 compleet
- [x] Edge banding (3 regimes) — Fase 7 compleet
