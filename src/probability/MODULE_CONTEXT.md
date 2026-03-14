# Probability Engine — MODULE_CONTEXT

## Wat
Berekent een gestructureerde kansupdate gegeven nieuws + marktcontext.

## Te bouwen (Fase 4 rule-based, Fase 6 LLM)
- `engine.py` — ProbabilityEngine: news + market → ProbabilityAssessment

## Interfaces
- **Input:** NormalizedNewsEvent + MarketCandidate (met resolution info)
- **Output:** ProbabilityAssessment

## Methodes
- **rule_based:** source tier + sentiment keywords → probability shift
- **llm:** (Fase 6) gestructureerde LLM prompt → parsed output
- **hybrid:** rule-based + LLM verificatie

## Config sectie: `probability.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 4 (rule-based) en Fase 6 (LLM)
