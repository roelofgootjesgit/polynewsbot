# Audit & Replay — MODULE_CONTEXT

## Wat
Volledige decision trace logging + historische replay van nieuwssequenties.

## Te bouwen (Fase 8)
- `logger.py` — Decision trace logger (JSON per event/decision)
- `replay.py` — Replay engine: historische events als live afspelen

## Interfaces
- **Input:** elke pipeline stap levert log entries
- **Output:** JSON decision logs, replay resultaten

## Moet loggen per event
- Welk bericht binnenkwam + wanneer
- Hoe het geclassificeerd werd
- Welke markt gekoppeld werd
- Hoe resolutie gelezen werd
- Welke model_probability berekend
- Marktprijs + orderboek op dat moment
- Edge gezien + waarom wel/niet gehandeld
- Hoe de positie verliep

## Config sectie: `audit.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 8
