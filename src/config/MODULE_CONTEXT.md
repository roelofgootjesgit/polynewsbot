# Config — MODULE_CONTEXT

## Wat
Config loading (YAML + .env + deep merge) en logging setup. Geadapteerd van OCLW bot.

## Bestanden
- `loader.py` — load_config(), _deep_merge(), env overrides
- `logging.py` — setup_logging(), timestamped log files

## Interfaces
- **Input:** configs/default.yaml + optionele override yaml + .env
- **Output:** dict[str, Any] config object dat door alle modules wordt gebruikt

## Env variabelen
POLYMARKET_API_KEY, POLYMARKET_SECRET, POLYMARKET_WALLET_PRIVATE_KEY,
POLYMARKET_CHAIN_ID, NEWSAPI_KEY, OPENAI_API_KEY, DRY_RUN, LOG_FILE, CONFIG_PATH

## Status
- [x] loader.py — YAML + env + deep merge
- [x] logging.py — console + file met timestamps
