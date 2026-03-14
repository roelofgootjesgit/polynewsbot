# Probability Engine — MODULE_CONTEXT

## Wat
Berekent een gestructureerde kansupdate gegeven nieuws + marktcontext.

## Bestanden
- `engine.py` — ProbabilityEngine: rule-based probability shift

## Interfaces
- **Input:** NormalizedNewsEvent + MarketCandidate + ResolutionMatch + current market probability
- **Output:** ProbabilityAssessment

## Methodes
- **rule_based (Fase 4):** source tier + sentiment keywords → probability shift
- **llm (Fase 6):** gestructureerde LLM prompt → parsed output

## Key logica
- `_detect_direction()`: keyword-based sentiment (positive/negative/neutral)
- `_calculate_shift()`: base shift * quality * novelty * resolution multipliers
- `_calculate_confidence()`: gewogen combinatie tier_score + resolution_match + novelty

## Config sectie: `probability.*` in default.yaml

## Status
- [x] Rule-based engine — Fase 4 compleet
- [ ] LLM engine — gepland Fase 6
