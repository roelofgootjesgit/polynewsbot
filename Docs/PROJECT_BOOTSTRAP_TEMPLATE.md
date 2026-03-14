# Project Bootstrap Template — Van Idee naar Werkend Systeem

Dit document beschrijft het exacte opstartproces dat we gebruikten voor de Polymarket News Bot.
Het is een herbruikbaar playbook voor elk volgend serieus tradingproject of softwareproject.

---

## Overzicht van het proces

```
1. Het Boek schrijven (conceptueel plan)
2. Bestaand project analyseren (code hergebruik)
3. Mentor Instructie definiëren (AI rol en regels)
4. Ontwikkelplan maken (fases, taken, context management)
5. Foundation bouwen (skeleton, config, models)
6. Iteratief doorontwikkelen per fase
```

---

## Stap 1 — Het Boek schrijven

**Wat:** Schrijf een conceptueel boek (of document) dat het volledige systeem beschrijft alsof je het aan iemand uitlegt die er niets van weet. Geen code — alleen ideeën, architectuur en logica.

**Waarom:** Dit dwingt je om scherp na te denken voordat je gaat bouwen. Het voorkomt dat je een bot bouwt die technisch werkt maar strategisch nergens op slaat.

**Structuur die wij gebruikten:**

| Hoofdstuk | Inhoud |
|---|---|
| 1 — Het Idee | Wat bouwen we en waarom? Waar zit de edge? |
| 2 — Hoe de markt werkt | Hoe werken prediction market prijzen? |
| 3 — Architectuur | Welke modules, welke pipeline, welke dataflow? |
| 4 — Integratie met bestaand project | Wat hergebruiken, wat vervangen, wat nieuw? |
| 5 — De echte edge | Waar komt winst vandaan? Snelheid, interpretatie, executie |
| 6 — Risico en schaalbaarheid | Position sizing, guardrails, portfolio management |

**Plus:** Een JSON-spec (`Json_info.txt`) met alle modules, data contracts, pipeline definitie en cursor-directieven. Dit fungeert als machineleesbaar architectuurdocument.

**Tip:** Schrijf dit in een LLM-chat (GPT/Claude) als een gesprek. Stel vragen, laat het uitwerken, corrigeer waar nodig. Kopieer de output naar `.txt` bestanden in een `Docs/` map.

---

## Stap 2 — Bestaand project analyseren

**Wat:** Als je een eerder project hebt (in ons geval de OCLW bot), laat Cursor het grondig doorlezen en een hergebruik-analyse maken.

**Waarom:** Je begint niet from scratch. Infra-patronen (config, logging, risk, state, tests) zijn universeel. Je wilt alleen de domein-specifieke intelligentie vervangen.

**Hoe wij dit deden:**

1. OCLW bot map delen met Cursor (`@pad/naar/project`)
2. Cursor leest: directory tree, entry points, config, risk, logging, base classes, pyproject.toml
3. Cursor maakt een hergebruik-matrix:

```
| OCLW bestand          | Hergebruik?     | Aanpassing           |
|-----------------------|-----------------|----------------------|
| config.py             | Ja, direct      | Andere parameters    |
| logging_config.py     | Ja, direct      | Rename env vars      |
| risk.py               | Patroon         | Andere regels        |
| strategy_modules/     | Nee, vervangen  | Nieuwe pipeline      |
| broker_adapter        | Nee, vervangen  | Polymarket adapter   |
```

**Resultaat:** Je weet precies wat je kopieert, wat je aanpast, en wat je from scratch bouwt.

---

## Stap 3 — Mentor Instructie definiëren

**Wat:** Een instructiedocument dat Cursor (of elke AI) vertelt wie hij is, hoe hij moet denken, en wat zijn rol is in het project.

**Waarom:** Zonder instructie gedraagt een AI zich als generieke tutorial-bot. Met instructie gedraagt hij zich als je senior architect/CTO.

**Onze mentor instructie bevat:**

1. **Roldefnitie** — senior hedge fund architect, quant mentor, systems engineer
2. **Denkorde** — strategische correctheid → edge locatie → architectuur → uitvoerbaarheid → risico → simpelste serieuze versie
3. **Response structuur** — objective, why it matters, inputs, outputs, logic, risks, build plan, next step
4. **Engineering principes** — modulair, auditeerbaar, guardrails first, deterministic core, AI only where useful
5. **Beschermingsregels** — pushback op vage strategie, fake edge, overengineering, missing guardrails
6. **Code regels** — productie-georiënteerd, clarity over cleverness, logs en configs als first-class citizens

**Tip:** Bewaar dit als `Docs/mentor instructie.txt` en refereer ernaar in Cursor rules of als context.

---

## Stap 4 — Ontwikkelplan maken met Context Management

**Wat:** Een `DEVELOPMENT_PLAN.md` dat het hele project opdeelt in fases met taken, en een protocol definieert om zuinig met tokens om te gaan.

**Waarom:** Zonder plan bouw je willekeurig. Zonder context management raakt je Cursor-sessie vol en verspil je tokens aan irrelevante context.

### Het plan bevat:

**A. Fases met concrete taken**
```
Fase 0 — Foundation (config, logging, models, skeleton)
Fase 1 — Externe adapter (API connectie)
Fase 2 — Data ingestion (bronnen, normalisatie)
Fase 3 — Filtering + mapping
Fase 4 — Kernlogica (edge, risk)
Fase 5 — Pipeline orchestratie
Fase 6 — AI upgrade
Fase 7 — Monitoring + exit
Fase 8 — Audit + replay
```

**B. Status tracker** — per taak ☐/☑ zodat je weet waar je bent.

**C. Context Management Protocol** — de sleutel tot token-efficiëntie:

### Context Management Protocol

**Probleem:** Een groot project heeft veel bestanden. Als Cursor elke sessie alles leest, kost dat tokens en vult de context.

**Oplossing: MODULE_CONTEXT.md per module**

Elke module map (`src/news/`, `src/edge/`, etc.) krijgt een eigen `MODULE_CONTEXT.md` bestand (~20 regels) met:
- Wat de module doet (1-2 zinnen)
- Welke bestanden erin zitten
- Inputs en outputs (data contracts)
- Interfaces met andere modules
- Huidige status

**Werkregels:**
1. Begin elke sessie met: "We werken aan [module]. Lees DEVELOPMENT_PLAN.md en src/[module]/MODULE_CONTEXT.md"
2. Cursor leest maximaal 2-3 context bestanden
3. Docs/ map wordt NIET meer gelezen — alles staat verwerkt in het plan
4. Oude project code wordt NIET geladen — alleen als je specifiek een patroon kopieert
5. Aan het eind van de sessie: update MODULE_CONTEXT.md met nieuwe status

**Sessie-start template:**
```
"We werken aan [module naam]. Lees:
1. DEVELOPMENT_PLAN.md (fase check)
2. src/[module]/MODULE_CONTEXT.md
3. [optioneel: aangrenzende module context]"
```

**Sessie-eind:**
1. Update MODULE_CONTEXT.md
2. Update status in DEVELOPMENT_PLAN.md (☐ → ☑)

---

## Stap 5 — Foundation bouwen

**Wat:** In de eerste sessie(s) bouw je het project skeleton:

1. `pyproject.toml` — dependencies, entry point, test config
2. `.gitignore` — excludes
3. `.env.example` — alle env variabelen gedocumenteerd
4. Config systeem — YAML + .env + deep merge (gekopieerd van oud project)
5. Logging — console + timestamped file (gekopieerd van oud project)
6. Data models — Pydantic models voor alle data contracts
7. Default config — alle secties met verstandige defaults
8. Module directories — `__init__.py` + `MODULE_CONTEXT.md` per module
9. CLI entry point — basis commandos
10. Eerste tests — config loading + model validatie
11. Git init + eerste commit + push

**Verificatie:** `pytest -v` moet groen zijn. CLI moet werkende output geven.

---

## Stap 6 — Iteratief bouwen per fase

Na de foundation werk je fase voor fase:

1. Lees de relevante MODULE_CONTEXT.md bestanden
2. Bouw de module
3. Schrijf tests (unit + integration waar mogelijk)
4. Verifieer: alle tests groen
5. Update MODULE_CONTEXT.md
6. Update DEVELOPMENT_PLAN.md status
7. Commit + push
8. Volgende fase

**Elke fase produceert:**
- Werkende code met tests
- Geüpdatete context bestanden
- Een commit met duidelijke beschrijving

---

## Bestandsstructuur (template)

```
project/
├── DEVELOPMENT_PLAN.md          ← master plan + status + context protocol
├── Docs/
│   ├── Hoofdstuk 1 - ...txt    ← conceptueel boek
│   ├── Hoofdstuk 2 - ...txt
│   ├── ...
│   ├── Json_info.txt            ← machineleesbare spec
│   └── mentor instructie.txt    ← AI rol instructie
├── configs/
│   ├── default.yaml             ← alle config secties
│   └── .env.example             ← env variabelen template
├── src/
│   ├── module_a/
│   │   ├── __init__.py
│   │   ├── MODULE_CONTEXT.md    ← mini-briefing voor Cursor
│   │   └── code.py
│   ├── module_b/
│   │   ├── __init__.py
│   │   ├── MODULE_CONTEXT.md
│   │   └── code.py
│   └── models/
│       ├── __init__.py
│       ├── MODULE_CONTEXT.md
│       └── *.py                 ← Pydantic data contracts
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── .gitignore
└── .env                         ← NIET in git
```

---

## Checklist voor een nieuw project

### Voorbereiding (voordat je Cursor opent)
- [ ] Conceptueel boek/plan geschreven (minimaal: idee + architectuur + edge + risico)
- [ ] JSON-spec met modules, pipeline, data contracts
- [ ] Mentor instructie gedefinieerd
- [ ] Oud project beschikbaar (als die er is) voor hergebruik-analyse

### Opstarten (eerste Cursor sessie)
- [ ] Oud project laten analyseren → hergebruik-matrix
- [ ] DEVELOPMENT_PLAN.md geschreven met fases + context protocol
- [ ] Fase 0 gebouwd: skeleton, config, logging, models, tests
- [ ] Git repo aangemaakt en eerste commit gepusht
- [ ] Alle MODULE_CONTEXT.md bestanden aangemaakt

### Per fase
- [ ] Context laden: DEVELOPMENT_PLAN.md + relevante MODULE_CONTEXT.md
- [ ] Module bouwen + tests
- [ ] Alle tests groen
- [ ] MODULE_CONTEXT.md geüpdatet
- [ ] DEVELOPMENT_PLAN.md status geüpdatet
- [ ] Commit + push

---

## Waarom dit werkt

1. **Het boek dwingt denkwerk af** — je bouwt niet blind, je bouwt met richting
2. **Hergebruik bespaart tijd** — infrastructure is 80% hetzelfde tussen projecten
3. **Mentor instructie verhoogt output kwaliteit** — Cursor gedraagt zich als CTO, niet als tutorial
4. **Fases voorkomen chaos** — je weet altijd wat af is en wat volgt
5. **Context management bespaart tokens** — 2-3 bestanden per sessie i.p.v. de hele codebase
6. **MODULE_CONTEXT.md is de brug** — tussen sessies raak je de draad niet kwijt
7. **Tests bij elke fase** — je breekt nooit eerder werk

---

## Toepassing op toekomstige projecten

Dit template werkt voor:
- Een nieuwe tradingbot (ander instrument, andere strategie)
- Een data pipeline project
- Een API-driven applicatie
- Elk project met meerdere modules en een duidelijke pipeline

Het enige dat verandert is de **inhoud** van het boek en de **modules** in het plan.
Het **proces** blijft hetzelfde.
