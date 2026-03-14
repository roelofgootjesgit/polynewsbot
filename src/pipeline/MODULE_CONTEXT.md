# Pipeline Orchestratie — MODULE_CONTEXT

## Wat
Verbindt alle modules in één event-driven pipeline. De hoofdcontroller.

## Te bouwen (Fase 5)
- `orchestrator.py` — EventPipeline: news → filter → map → edge → execute

## Pipeline flow
```
news_ingestion
  → normalization
    → relevance_filter
      → market_mapping
        → resolution_check
          → probability_update
            → market_state_check
              → edge_engine
                → risk_veto
                  → execution
                    → monitoring
```

## Interfaces
- **Input:** timer tick of news event trigger
- **Output:** trade decisions, position updates, audit logs

## Modes
- dry_run: hele pipeline zonder echte orders
- live: met executie
- replay: historische events afspelen

## Config sectie: `execution.dry_run` flag

## Status
- [ ] Niet gestart — gepland voor Fase 5
