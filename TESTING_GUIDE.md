# Polymarket News Bot — Test Guide

Stap-voor-stap handleiding om de bot te testen in PowerShell.
Alle commando's uitvoeren vanuit de projectmap.

---

## 0. Navigeer naar de projectmap

```powershell
cd c:\Users\Gebruiker\Polymarket_news_bot
```

---

## 1. Virtual environment activeren

```powershell
.venv\Scripts\Activate.ps1
```

Je ziet nu `(.venv)` voor je prompt. Als dit niet werkt:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

---

## 2. Unit tests draaien (100 tests, geen internet nodig)

Alle unit tests:

```powershell
python -m pytest tests/unit/ -v
```

Alleen een specifieke module testen:

```powershell
python -m pytest tests/unit/test_probability.py -v
python -m pytest tests/unit/test_edge.py -v
python -m pytest tests/unit/test_risk.py -v
python -m pytest tests/unit/test_pipeline.py -v
```

Verwacht resultaat: `100 passed`

---

## 3. Config check (geen internet nodig)

```powershell
python -m src.cli status
```

Verwacht resultaat:
```
Polymarket News Bot v0.1.0
Mode: DRY RUN
Config loaded: 12 sections
  [audit]
  [edge]
  [execution]
  ...
```

---

## 4. Single pipeline cycle (internet nodig)

Dit doet in één keer:
- Nieuws ophalen van RSS feeds (Reuters, CoinDesk)
- 1000 Polymarket events + 6000 markten laden
- Nieuws filteren, matchen, edge berekenen, guardrails checken

```powershell
python -m src.cli cycle
```

Verwacht resultaat (voorbeeld):
```
Pipeline setup — mode: DRY RUN
News sources: 2
Total active events fetched: 1000
Universe loaded: 1000 events -> 5862 tradeable markets
Poll complete: 25 new events from 2 sources
Relevance filter: 21/25 events passed
Result: polled=25 -> filtered=21 -> matched=33 -> edges=33 -> approved=0 -> executed=0 (vetoed=33)
Pipeline shutdown complete
```

Let op: `vetoed=33` is normaal — de rule-based engine is conservatief.

---

## 5. Meerdere cycles draaien (polling loop)

3 cycles met automatisch wachten (30 sec tussen cycles):

```powershell
python -m src.cli run --cycles 3
```

Stoppen: druk `Ctrl+C`

---

## 6. Decision logs bekijken

Na een cycle staan de beslissingen in `logs/decisions/`:

```powershell
Get-ChildItem logs\decisions\
```

Eén beslissing bekijken (eerste regel van het logbestand):

```powershell
Get-Content logs\decisions\decisions_2026-03-14.jsonl -First 1 | python -m json.tool
```

Alle gevetode beslissingen tellen:

```powershell
(Select-String -Path logs\decisions\*.jsonl -Pattern "vetoed").Count
```

---

## 7. Integration tests (internet nodig, duurt ~30 sec)

Deze tests praten met de echte Polymarket API:

```powershell
python -m pytest tests/integration/ -v
```

Sommige tests kunnen `SKIP` zijn als er geen orderbook beschikbaar is — dat is normaal.

---

## 8. Debug scripts (optioneel)

### Wat zien de newsfeeds?

```powershell
python scripts/debug_cycle.py
```

Toont: welke headlines binnenkomen, relevance scores, en welke markten matchen.

### Werkt de orderbook connectie?

```powershell
python scripts/debug_orderbook.py
```

Toont: orderbook data voor Bitcoin-markten (bid, ask, spread, liquiditeit).

---

## Samenvatting commando's

| Wat | Commando |
|-----|----------|
| Tests draaien | `python -m pytest tests/unit/ -v` |
| Config check | `python -m src.cli status` |
| Één cycle | `python -m src.cli cycle` |
| Loop (3x) | `python -m src.cli run --cycles 3` |
| Loop (oneindig) | `python -m src.cli run` |
| Decision logs | `Get-Content logs\decisions\*.jsonl -First 1 \| python -m json.tool` |
| Debug news | `python scripts/debug_cycle.py` |
| Debug orderbook | `python scripts/debug_orderbook.py` |

---

## Veelvoorkomende issues

**"No module named src"**
→ Zorg dat je in de projectmap staat (`cd c:\Users\Gebruiker\Polymarket_news_bot`)

**"venv not found"**
→ Maak opnieuw: `python -m venv .venv` en dan `pip install -e ".[dev]"`

**Unicode errors in de console**
→ Run dit eerst: `$env:PYTHONIOENCODING="utf-8"`

**Alles vetoed (approved=0)**
→ Normaal voor de rule-based engine. Het nieuws van RSS (CoinDesk) matcht op "Bitcoin Up or Down" markten, maar er is geen echte edge. Fase 6 (LLM) maakt dit slimmer.
