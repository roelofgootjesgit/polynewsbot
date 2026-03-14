# Risk & Guardrails — MODULE_CONTEXT

## Wat
Veto-logica + position sizing + portfolio exposure. Staat los van de intelligentielaag.

## Te bouwen (Fase 4)
- `guardrails.py` — Veto checks (source tier, spread, confidence, exposure, etc.)
- `sizing.py` — Position sizing (max % per trade, per cluster, totaal)
- `exposure.py` — Portfolio exposure tracking per event cluster

## Interfaces
- **Input:** TradeDecision (pre-approval) + huidige portfolio state
- **Output:** TradeDecision met guardrail_status (passed/vetoed) en position_size_usd

## Veto regels (uit docs)
- Niet traden op onbevestigde bronnen (tier 4 alleen)
- Niet traden bij onduidelijke resolutie
- Niet traden bij te grote spread
- Niet traden boven max exposure per cluster
- Niet traden bij lage confidence
- Niet traden bij tegenstrijdige signalen

## OCLW hergebruik: patroon van risk.py en sizing.py

## Config sectie: `risk.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 4
