# Polymarket News Bot — Ontwikkelplan

## Project identiteit

**Naam:** Polymarket News Trading Bot
**Doel:** Event-driven AI news trading systeem voor prediction markets.
**Core thesis:** `informatie → kansupdate → edge → executie`
**Basis:** Hergebruik OCLW bot patronen voor infrastructuur, bouw nieuwe intelligentielaag.

---

## Context Management Protocol (Token-zuinig werken)

### Probleem
Dit project heeft veel documentatie en zal veel code krijgen. Als we elke sessie alles meeslepen, verspillen we tokens en raakt de context vol.

### Oplossing: Module-isolatie met context files

Elke module krijgt een eigen `MODULE_CONTEXT.md` bestand in zijn map. Dit bestand bevat:
- Wat de module doet (1-2 zinnen)
- Inputs en outputs (data contracts)
- Interfaces met andere modules
- Huidige status (wat is af, wat niet)
- Bekende issues of beslissingen

**Werkwijze per sessie:**
1. Vertel aan het begin van een sessie welke module je wilt bouwen (bijv. "we werken aan de edge engine")
2. Cursor leest ALLEEN de `MODULE_CONTEXT.md` van die module + eventueel aangrenzende modules
3. Geen hele docs map, geen hele codebase — alleen wat relevant is
4. Aan het eind van de sessie updaten we de `MODULE_CONTEXT.md` met de nieuwe status

**Regels:**
- Refereer naar `DEVELOPMENT_PLAN.md` voor de grote lijn (dit bestand)
- Refereer naar de module's eigen `MODULE_CONTEXT.md` voor de details
- Lees OCLW code alleen als je specifiek een patroon wilt overnemen
- Lees de Docs/ map NIET meer — alles relevants staat al verwerkt in dit plan en de module contexts
- Maximaal 2-3 bestanden context aan het begin van een sessie

### Context bestanden structuur
```
src/
├── config/
│   └── MODULE_CONTEXT.md       ← config systeem
├── news/
│   └── MODULE_CONTEXT.md       ← news ingestion
├── filter/
│   └── MODULE_CONTEXT.md       ← relevance filter
├── mapping/
│   └── MODULE_CONTEXT.md       ← market mapping
├── resolution/
│   └── MODULE_CONTEXT.md       ← resolution understanding
├── probability/
│   └── MODULE_CONTEXT.md       ← probability engine
├── market_state/
│   └── MODULE_CONTEXT.md       ← market state analyzer
├── edge/
│   └── MODULE_CONTEXT.md       ← edge engine
├── execution/
│   └── MODULE_CONTEXT.md       ← polymarket adapter + order management
├── risk/
│   └── MODULE_CONTEXT.md       ← guardrails + risk
├── monitor/
│   └── MODULE_CONTEXT.md       ← position monitor + exit
├── audit/
│   └── MODULE_CONTEXT.md       ← logging, audit, replay
└── pipeline/
    └── MODULE_CONTEXT.md       ← event pipeline orchestratie
```

### Sessie-start template
```
"We werken aan [module naam]. Lees:
1. DEVELOPMENT_PLAN.md (fase check)
2. src/[module]/MODULE_CONTEXT.md
3. [optioneel: aangrenzende module context als er interface-afhankelijkheid is]"
```

---

## Projectstructuur

```
Polymarket_news_bot/
├── DEVELOPMENT_PLAN.md          ← dit bestand (master plan)
├── Docs/                        ← originele docs (niet meer lezen na setup)
├── configs/
│   ├── default.yaml             ← basis config
│   └── .env.example             ← environment variabelen template
├── src/
│   ├── __init__.py
│   ├── models/                  ← Pydantic data models (gedeeld)
│   │   ├── __init__.py
│   │   ├── events.py            ← NormalizedNewsEvent, SourceTier
│   │   ├── markets.py           ← MarketCandidate, MarketState
│   │   ├── probability.py       ← ProbabilityAssessment
│   │   ├── trades.py            ← TradeDecision, Position
│   │   └── MODULE_CONTEXT.md
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py            ← YAML + env config (van OCLW)
│   │   └── MODULE_CONTEXT.md
│   ├── news/
│   │   ├── __init__.py
│   │   ├── base.py              ← ABC NewsSource
│   │   ├── rss.py               ← RSS feed source
│   │   ├── newsapi.py           ← NewsAPI source
│   │   ├── polymarket_feed.py   ← Polymarket activity feed
│   │   ├── normalizer.py        ← Naar NormalizedNewsEvent
│   │   └── MODULE_CONTEXT.md
│   ├── filter/
│   │   ├── __init__.py
│   │   ├── relevance.py         ← RelevanceFilter
│   │   └── MODULE_CONTEXT.md
│   ├── mapping/
│   │   ├── __init__.py
│   │   ├── market_mapper.py     ← News → Market koppeling
│   │   ├── universe.py          ← Market universe config
│   │   └── MODULE_CONTEXT.md
│   ├── resolution/
│   │   ├── __init__.py
│   │   ├── parser.py            ← Resolution criteria interpreter
│   │   └── MODULE_CONTEXT.md
│   ├── probability/
│   │   ├── __init__.py
│   │   ├── engine.py            ← Probability update engine
│   │   └── MODULE_CONTEXT.md
│   ├── market_state/
│   │   ├── __init__.py
│   │   ├── analyzer.py          ← Orderboek, spread, liquiditeit
│   │   └── MODULE_CONTEXT.md
│   ├── edge/
│   │   ├── __init__.py
│   │   ├── engine.py             ← Edge berekening + drempels
│   │   └── MODULE_CONTEXT.md
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── polymarket_client.py  ← Polymarket API wrapper
│   │   ├── order_manager.py      ← Order lifecycle
│   │   └── MODULE_CONTEXT.md
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── guardrails.py         ← Veto logica
│   │   ├── sizing.py             ← Position sizing
│   │   ├── exposure.py           ← Portfolio exposure tracking
│   │   └── MODULE_CONTEXT.md
│   ├── monitor/
│   │   ├── __init__.py
│   │   ├── position_monitor.py   ← Thesis validity tracking
│   │   ├── exit_logic.py         ← Exit beslissingen
│   │   └── MODULE_CONTEXT.md
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── logger.py             ← Decision trace logging
│   │   ├── replay.py             ← Replay engine
│   │   └── MODULE_CONTEXT.md
│   └── pipeline/
│       ├── __init__.py
│       ├── orchestrator.py       ← Event pipeline controller
│       └── MODULE_CONTEXT.md
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── regression/
├── scripts/
│   ├── run_bot.py                ← Main entry point
│   └── replay.py                 ← Replay historische events
├── logs/
├── data/
│   └── state.json
├── pyproject.toml
├── requirements.txt
└── .gitignore
```

---

## Ontwikkelfases

### FASE 0 — Foundation (sessie 1-2)
**Doel:** Project skeleton + herbruikbare OCLW infrastructuur.

| # | Taak | OCLW hergebruik | Status |
|---|------|-----------------|--------|
| 0.1 | Project init: pyproject.toml, requirements.txt, .gitignore, git init | Patroon van OCLW | ☑ |
| 0.2 | Config systeem: loader.py (YAML + .env + deep merge) | Kopie + aanpassing van OCLW config.py | ☑ |
| 0.3 | Logging setup: console + file, timestamped runs | Kopie van OCLW logging_config.py | ☑ |
| 0.4 | Pydantic data models: NormalizedNewsEvent, MarketCandidate, ProbabilityAssessment, TradeDecision | Nieuw (OCLW Trade als inspiratie) | ☑ |
| 0.5 | Default.yaml met alle config secties (placeholder waardes) | OCLW structuur als basis | ☑ |
| 0.6 | MODULE_CONTEXT.md voor elke module map | Nieuw | ☑ |

**Klaar wanneer:** `python -c "from src.config.loader import load_config; print(load_config())"` werkt.

---

### FASE 1 — Polymarket Adapter (sessie 3-4)
**Doel:** Verbinding met Polymarket. Markten lezen, orderboek ophalen, orders plaatsen.

| # | Taak | Details |
|---|------|---------|
| 1.1 | Polymarket API client: auth, markten ophalen, orderboek lezen | py-clob-client of REST |
| 1.2 | Market universe loader: actieve markten cachen + filteren | Config-driven whitelist |
| 1.3 | Market state analyzer: bid/ask, spread, diepte, liquiditeit score | MarketState model vullen |
| 1.4 | Order plaatsing: buy/sell YES/NO, limit orders | Met wallet signing |
| 1.5 | Order manager: order tracking, fills, cancel | State persistence (JSON) |
| 1.6 | Integration test: haal echte markten op, lees orderboek | Testnet of read-only |

**Klaar wanneer:** Bot kan markten ophalen, orderboek lezen, en een testorder plaatsen.

**Afhankelijkheden:** Polymarket API key, wallet private key.

---

### FASE 2 — News Ingestion + Normalisatie (sessie 5-6)
**Doel:** Nieuws ophalen uit meerdere bronnen, normaliseren naar intern formaat.

| # | Taak | Details |
|---|------|---------|
| 2.1 | ABC NewsSource interface | fetch() → List[RawNewsItem] |
| 2.2 | RSS feed source (bijv. Reuters, AP, Coindesk) | feedparser |
| 2.3 | NewsAPI source | newsapi-python |
| 2.4 | Normalizer: raw → NormalizedNewsEvent | Source tier, reliability score, timestamp |
| 2.5 | Deduplicatie: zelfde nieuws van meerdere bronnen filteren | Hash op headline + tijdsvenster |
| 2.6 | Poller: periodiek bronnen checken | Async loop |

**Klaar wanneer:** Bot haalt live nieuws op en produceert NormalizedNewsEvent objecten.

---

### FASE 3 — Relevance Filter + Market Mapping (sessie 7-8)
**Doel:** Bepaal of nieuws relevant is en koppel aan juiste Polymarket markt.

| # | Taak | Details |
|---|------|---------|
| 3.1 | Keyword/topic relevance filter (rule-based) | Config-driven keywords per categorie |
| 3.2 | Time relevance: is het nieuws vers genoeg? | Max age threshold |
| 3.3 | Market mapping: news topic → market cluster → specifieke markt | Twee-staps mapping |
| 3.4 | Resolution text ophalen per markt | Polymarket API |
| 3.5 | Mapping confidence score | Hoe zeker is de koppeling? |

**Klaar wanneer:** News event → relevante Polymarket markt met mapping confidence.

---

### FASE 4 — Edge Engine + Risk (sessie 9-10)
**Doel:** Bepaal of een trade de moeite waard is + guardrails.

| # | Taak | Details |
|---|------|---------|
| 4.1 | Simple probability engine (rule-based) | Source tier + sentiment → probability shift |
| 4.2 | Edge berekening: model_prob - market_prob - kosten | Net edge formule |
| 4.3 | Edge drempels: minimum raw edge, minimum net edge | Config-driven |
| 4.4 | Position sizing: max % per trade, per cluster, totaal | Van OCLW risk.py patroon |
| 4.5 | Guardrails: veto logica (bron te zwak, spread te groot, etc.) | Onafhankelijk van intelligentie |
| 4.6 | Exposure tracker: portfolio-breed risico bijhouden | Event cluster grouping |

**Klaar wanneer:** Gegeven een news event + markt → go/no-go trade beslissing met sizing.

---

### FASE 5 — Pipeline Orchestratie (sessie 11-12)
**Doel:** Alle modules verbinden in één event-driven pipeline.

| # | Taak | Details |
|---|------|---------|
| 5.1 | Pipeline orchestrator: news → filter → map → edge → execute | Sequentiële chain |
| 5.2 | Decision logging: elke stap loggen met volledige context | Audit trail |
| 5.3 | Main loop: poller + pipeline + sleep cycle | Entry point script |
| 5.4 | Dry-run mode: hele pipeline zonder echte orders | Config flag |
| 5.5 | Health check: is alles connected en draaiend? | Status endpoint / log |

**Klaar wanneer:** Bot draait end-to-end in dry-run mode op live nieuws.

---

### FASE 6 — AI Interpretatie Upgrade (sessie 13-15)
**Doel:** Vervang rule-based interpretatie door LLM voor complexere analyse.

| # | Taak | Details |
|---|------|---------|
| 6.1 | Resolution understanding via LLM | Resolutietekst → gestructureerde criteria |
| 6.2 | AI relevance filter | LLM als second opinion na keyword filter |
| 6.3 | AI probability engine | LLM → gestructureerde kansupdate |
| 6.4 | Prompt engineering + output parsing | Pydantic output validation |
| 6.5 | LLM cost tracking | Tokens per beslissing loggen |
| 6.6 | Fallback: als LLM faalt → rule-based | Graceful degradation |

**Klaar wanneer:** Bot gebruikt LLM voor interpretatie met fallback naar rules.

---

### FASE 7 — Position Monitor + Exit (sessie 16-17)
**Doel:** Posities volgen op thesis-validity en intelligent sluiten.

| # | Taak | Details |
|---|------|---------|
| 7.1 | Position monitor: track open posities + current P&L | Periodieke check |
| 7.2 | Thesis validity check: nieuw nieuws dat thesis verandert | Re-evaluate bij nieuwe events |
| 7.3 | Exit logic: take profit, force exit, time exit, reduce only | Meerdere exit modes |
| 7.4 | Repricing detection: markt heeft edge al geabsorbeerd | Exit trigger |

**Klaar wanneer:** Bot beheert posities actief en sluit op basis van thesis-validity.

---

### FASE 8 — Audit, Replay & Optimalisatie (sessie 18-20)
**Doel:** Volledige traceerbaarheid + historische replay + performance meting.

| # | Taak | Details |
|---|------|---------|
| 8.1 | Decision trace logger: elk event → volledige beslissingsketen | JSON per event |
| 8.2 | Replay engine: historische events afspelen als live | Zonder future leakage |
| 8.3 | Performance metrics: hit rate, edge accuracy, P&L | Dashboard of rapport |
| 8.4 | Source quality tracking: welke bronnen leveren edge? | Per-source statistieken |
| 8.5 | Baseline + regression tests | OCLW patroon overnemen |

**Klaar wanneer:** Elke beslissing is reconstrueerbaar en historische runs zijn replaybaar.

---

## OCLW Hergebruik Matrix

| OCLW bestand | Hergebruik in Polymarket bot | Aanpassing |
|---|---|---|
| `src/trader/config.py` | `src/config/loader.py` | Andere parameters, zelfde mechanisme |
| `src/trader/logging_config.py` | `src/audit/logger.py` | Uitbreiden met decision trace |
| `src/trader/execution/risk.py` | `src/risk/guardrails.py` | Prediction market regels |
| `src/trader/execution/sizing.py` | `src/risk/sizing.py` | Share-based i.p.v. lot-based |
| `src/trader/execution/order_manager.py` | `src/execution/order_manager.py` | Polymarket order lifecycle |
| `src/trader/data/schema.py` (Trade) | `src/models/trades.py` | YES/NO shares, probability velden |
| `src/trader/strategy_modules/base.py` | Inspiratie voor module ABC's | Andere interface (geen candle data) |
| `src/trader/backtest/metrics.py` | `src/audit/` performance metrics | Andere KPI's |
| `configs/default.yaml` structuur | `configs/default.yaml` | Andere secties |

---

## Sessie-protocol

### Begin van een sessie
1. Vertel welke module/fase je wilt bouwen
2. Cursor leest `DEVELOPMENT_PLAN.md` (dit bestand) — check fase status
3. Cursor leest de relevante `MODULE_CONTEXT.md` bestanden (max 2-3)
4. Bouw

### Eind van een sessie
1. Update `MODULE_CONTEXT.md` van de module(s) waar je aan werkte
2. Update de status kolom in dit bestand (☐ → ☑)
3. Noteer eventuele beslissingen of open vragen

### Regels
- **Niet** de hele Docs/ map lezen (staat al verwerkt in dit plan)
- **Niet** de hele OCLW codebase laden (alleen specifieke bestanden als je een patroon overneemt)
- **Niet** meer dan 3 MODULE_CONTEXT bestanden tegelijk lezen
- **Wel** vertrouwen op de data contracts in `src/models/` als bron van waarheid
- **Wel** elke module onafhankelijk testbaar houden
- **Wel** dry-run mode als eerste milestone per fase

---

## Prioriteiten (mentor principes)

1. **Edge before features** — alleen bouwen wat edge oplevert
2. **Structure before speed** — goede architectuur eerst
3. **Guardrails before autonomy** — veto logica vóór AI vrijheid
4. **Logs before scaling** — audit trail vóór meer markten
5. **Replay before confidence** — bewijs vóór vertrouwen
6. **Disciplined iteration** — kleine stappen, werkend systeem

---

## Technische keuzes

| Keuze | Beslissing | Reden |
|---|---|---|
| Taal | Python 3.11+ | Consistent met OCLW |
| Data models | Pydantic v2 | Validatie + serialisatie |
| Config | YAML + .env | Bewezen in OCLW |
| HTTP | httpx (async) | Sneller dan requests voor polling |
| Polymarket | py-clob-client | Officiële CLOB client |
| LLM | OpenAI API (later) | Fase 6, niet eerder |
| News feeds | feedparser + newsapi | Simpel, betrouwbaar |
| Testing | pytest | Consistent met OCLW |
| Logging | stdlib logging | Consistent met OCLW |
| Async | asyncio | Voor news polling + market data |

---

## Status tracker

| Fase | Naam | Sessies | Status |
|---|---|---|---|
| 0 | Foundation | 1-2 | ☑ Afgerond |
| 1 | Polymarket Adapter | 3-4 | ☐ Niet gestart |
| 2 | News Ingestion | 5-6 | ☐ Niet gestart |
| 3 | Relevance + Mapping | 7-8 | ☐ Niet gestart |
| 4 | Edge + Risk | 9-10 | ☐ Niet gestart |
| 5 | Pipeline Orchestratie | 11-12 | ☐ Niet gestart |
| 6 | AI Interpretatie | 13-15 | ☐ Niet gestart |
| 7 | Position Monitor | 16-17 | ☐ Niet gestart |
| 8 | Audit + Replay | 18-20 | ☐ Niet gestart |
