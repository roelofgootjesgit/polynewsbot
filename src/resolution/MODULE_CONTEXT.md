# Resolution Understanding — MODULE_CONTEXT

## Wat
Rule-based interpretatie van markt resolutietekst. Beschermt tegen te losse interpretaties.

## Bestanden
- `parser.py` — ResolutionParser, ResolutionCriteria, ResolutionMatch

## ResolutionParser
- `parse_criteria(market)` → ResolutionCriteria (key phrases, deadline, type, official source required)
- `match_event(event, criteria)` → ResolutionMatch (score, matched phrases, sufficient_for_trade)

## Resolution types gedetecteerd
- threshold (price above/below X)
- binary (yes/no)
- multi_outcome (who will win)
- date (by/before deadline)

## Key phrases extraction
- Regex patterns voor "resolves to yes if...", "will resolve if..."
- Resolution keywords (announce, approve, sign, pass, reach, exceed, etc.)

## Hard rule: geen trade als resolution understanding onvoldoende zeker is (min_understanding_confidence)

## Fase 6: LLM upgrade voor complexe resolutieteksten

## Config sectie: `resolution.*` in default.yaml

## Status
- [x] parser.py — rule-based parsing + matching
- [x] Unit tests (7 passing)
- [ ] LLM-based parsing — gepland voor Fase 6
