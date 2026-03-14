# Pipeline Orchestratie — MODULE_CONTEXT

## Wat
Verbindt alle modules in één event-driven pipeline. De hoofdcontroller.

## Bestanden
- `orchestrator.py` — EventPipeline: news → filter → map → edge → execute

## Pipeline flow
```
NewsPoller.poll()
  → RelevanceFilter.filter_batch()
    → MarketMapper.map_event()
      → ResolutionParser.parse_criteria() + match_event()
        → ProbabilityEngine.assess()
          → MarketStateAnalyzer.analyze() (via CLOB orderbook)
            → EdgeEngine.evaluate()
              → Guardrails.evaluate()
                → OrderManager.submit_order() (dry-run of live)
```

## Classes
- **EventPipeline**: hoofdcontroller, bezit alle modules
  - `setup()` — init connections, load universe, load state
  - `run_loop(max_cycles)` — poll → process → sleep → repeat
  - `run_cycle()` → PipelineStats
  - `_process_event()` — één event door hele keten
  - `_evaluate_candidate()` — één markt evalueren
  - `_execute_trade()` — order plaatsen (dry-run of live)
- **PipelineStats**: tellers per cycle

## Modes
- `execution.dry_run: true` → hele pipeline zonder echte orders
- `execution.dry_run: false` → live trading
- CLI: `newsbot run --cycles 1` voor single cycle

## Decision logging
- Elke event krijgt een DecisionTrace (via audit/decision_logger.py)
- Elke stap (filter, mapping, edge, guardrail, execution) wordt gelogd
- Flushed naar JSONL na elke cycle

## Status
- [x] Pipeline orchestrator — Fase 5 compleet
- [x] Decision logger — Fase 5 compleet
- [x] CLI commands (run, cycle, status) — Fase 5 compleet
- [x] 12 unit tests passing
