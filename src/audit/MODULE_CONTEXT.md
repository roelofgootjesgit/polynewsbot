# Audit, Replay & Performance — MODULE_CONTEXT

## Wat
Volledige traceerbaarheid van elke beslissing, historische replay van decision logs,
en performance meting met per-source/per-band/per-method attributie.

## Bestanden
- `decision_logger.py` — DecisionLogger + DecisionTrace: JSONL logging per event
- `replay.py` — ReplayEngine: laad historische logs, enriche en analyseer
- `performance.py` — PerformanceTracker + TradeRecord: P&L, win rate, attributie
- `reporter.py` — PerformanceReporter: console + markdown rapport generatie

## Interfaces
- **DecisionLogger.create_trace()** — start trace voor een event
- **DecisionLogger.flush()** — schrijf naar JSONL
- **ReplayEngine.load_events()** — laad + enriche historische events
- **ReplayEngine.replay()** — compute aggregate ReplayResult
- **PerformanceTracker.record_trade()** — registreer trade voor tracking
- **PerformanceTracker.compute_metrics()** — bereken PerformanceMetrics
- **PerformanceReporter.console_replay_report()** — print replay stats
- **PerformanceReporter.console_performance_report()** — print trade metrics
- **PerformanceReporter.markdown_report()** — genereer MD rapport

## CLI commando's
- `newsbot replay [--date-from] [--date-to] [--markdown path]`
- `newsbot report [--date-from] [--date-to] [-o path]`

## Attributie dimensies
- Per edge band (strong/normal/observe)
- Per source (Reuters, CoinDesk, etc.)
- Per method (rule_based, llm, hybrid)
- Per exit reason
- Veto reason frequency

## Config sectie: `audit.*` in default.yaml

## Status
- [x] Decision trace logger — Fase 5 compleet
- [x] Replay engine — Fase 8 compleet
- [x] Performance tracker — Fase 8 compleet
- [x] Reporter (console + markdown) — Fase 8 compleet
- [x] CLI integratie — Fase 8 compleet
- [x] 14 unit tests passing
