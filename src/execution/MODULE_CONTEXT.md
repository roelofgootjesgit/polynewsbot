# Execution — MODULE_CONTEXT

## Wat
Polymarket API adapter + order lifecycle management.

## Te bouwen (Fase 1)
- `polymarket_client.py` — API wrapper: markten ophalen, orderboek, orders plaatsen, wallet signing
- `order_manager.py` — Order tracking, fills, cancel, state persistence

## Interfaces
- **Input:** TradeDecision (van edge engine, na risk approval)
- **Output:** Order geplaatst, fill info, position created

## Polymarket specifiek
- YES/NO shares (niet klassieke assets)
- CLOB (Central Limit Order Book) via py-clob-client
- Wallet signing vereist voor orders

## Config sectie: `polymarket.*` en `execution.*` in default.yaml

## Status
- [ ] Niet gestart — gepland voor Fase 1
