# Execution — MODULE_CONTEXT

## Wat
Polymarket API adapter + order lifecycle management.

## Bestanden
- `polymarket_client.py` — Unified client: Gamma API (market data) + CLOB API (trading)
- `order_manager.py` — Order tracking, fills, cancel, dry-run mode, state persistence

## PolymarketClient
- `connect()` — init CLOB client, optioneel met wallet auth
- `get_events()`, `get_markets()`, `get_all_active_events()` — Gamma API (public, no auth)
- `get_event_by_slug()` — specifiek event ophalen
- `get_orderbook()`, `get_price()`, `get_midpoint()` — CLOB API
- `place_order()`, `cancel_order()`, `cancel_all_orders()` — trading (auth vereist)
- `get_positions()` — huidige posities

## OrderManager
- `submit_order()` — plaatst order of simuleert in dry-run
- `cancel()` — cancel order
- `save_state()` / `load_state()` — JSON state persistence
- ManagedOrder model met status tracking

## Config secties: `polymarket.*` en `execution.*`

## Status
- [x] polymarket_client.py — Gamma + CLOB API
- [x] order_manager.py — dry-run + state persistence
- [x] Unit tests (4 passing)
- [x] Integration tests (5 passing + 1 skip)
