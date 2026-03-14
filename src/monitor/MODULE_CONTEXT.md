# Position Monitor — MODULE_CONTEXT

## Wat
Volgt open posities op thesis-validity en beslist over exits.

## Te bouwen (Fase 7)
- `position_monitor.py` — Track posities, re-evaluate bij nieuw nieuws
- `exit_logic.py` — Exit beslissingen: take profit, force exit, time exit, reduce

## Interfaces
- **Input:** list[Position] + nieuwe NormalizedNewsEvents + MarketState updates
- **Output:** Exit signalen, position updates

## Exit modes
- Take profit bij snelle repricing
- Force exit als thesis ongeldig wordt
- Reduce only bij oplopende onzekerheid
- Time exit als edge niet materialiseert
- Flatten voor onbetrouwbare phase changes

## Config sectie: `monitor.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 7
