# Position Monitor — MODULE_CONTEXT

## Wat
Bewaakt open posities op thesis-validity, repricing completion, en exit signalen.
Sluit posities automatisch bij invalidatie, time-limit, of repricing-complete.

## Bestanden
- `position_monitor.py` — PositionMonitor: thesis state machine + exit signal detectie
- `exit_engine.py` — ExitEngine: voert exits uit via OrderManager
- `counter_news.py` — CounterNewsDetector: detecteert tegenstrijdig nieuws voor open posities

## Interfaces
- **PositionMonitor.register_position()** — registreer nieuwe positie voor monitoring
- **PositionMonitor.check_position()** — check één positie, return PositionSnapshot met exit signal
- **PositionMonitor.check_all()** — check alle open posities
- **PositionMonitor.invalidate_thesis() / weaken_thesis()** — thesis state management
- **ExitEngine.process_exits()** — verwerk alle exit signals, sluit posities
- **CounterNewsDetector.check_against_positions()** — check nieuw nieuws vs open posities

## Thesis State Machine
- `VALID` — thesis houdt stand, geen actie
- `WEAKENED` — tegenstrijdig signaal van zwakke bron, geen auto-exit
- `INVALIDATED` — tegenstrijdig nieuws van sterke bron, auto-exit als force_exit enabled
- `EXPIRED` — time limit bereikt

## Exit Triggers
1. Thesis invalidated door counter-news
2. Repricing complete (edge absorbed >= 70%)
3. Time limit bereikt (default 72h)

## Config sectie: `monitor.*` in default.yaml

## Status
- [x] Position monitor met thesis state — Fase 7 compleet
- [x] Exit engine — Fase 7 compleet
- [x] Counter-news detection — Fase 7 compleet
- [x] Pipeline integratie — Fase 7 compleet
- [x] 18 unit tests passing
