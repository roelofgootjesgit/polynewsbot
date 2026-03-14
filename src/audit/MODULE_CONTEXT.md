# Audit & Replay — MODULE_CONTEXT

## Wat
Decision trace logging + (later) historische replay van nieuwssequenties.

## Bestanden
- `decision_logger.py` — DecisionLogger + DecisionTrace: JSON-lines per event

## Interfaces
- **Input:** pipeline stappen leveren data per event
- **Output:** JSONL decision logs in `logs/decisions/decisions_YYYY-MM-DD.jsonl`

## DecisionTrace logvelden per event
- event info (source, tier, headline, topics)
- mapping (candidates count, best match, cluster)
- resolution (type, match_score, matched_phrases) per market
- market_state (bid, ask, spread, implied_prob, liquidity) per market
- probability (model_prob, confidence, direction) per market
- edge (side, raw_edge, net_edge, execution_allowed) per market
- guardrail (approved/vetoed, reasons, size_usd) per market
- execution (order_id, price, shares, dry_run, status) per market
- outcome (executed / vetoed / no_match)

## Config sectie: `audit.*` in default.yaml

## Status
- [x] DecisionLogger + DecisionTrace — Fase 5 compleet
- [ ] Replay engine — gepland voor Fase 8
