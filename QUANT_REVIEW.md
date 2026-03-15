# Quant Review — GO/NO-GO Assessment

**Datum:** 14 maart 2026
**Status:** Conditional GO — met required fixes voor first micro-live

---

## Oordeel in één zin

De architectuur is strategisch correct, maar de bottleneck zit nu volledig in calibration van approval, sizing en post-trade monitoring — niet meer in "de bot bouwen".

---

## Wat sterk is

- Juiste architectuur: `news → relevance → mapping → resolution → probability → edge → risk veto → execution`
- Guardrails als onafhankelijke veto-laag — AI kan veiligheidslaag niet overrulen
- Nette edge-berekening met fees, slippage, uncertainty penalty
- Sizing al exposure-aware (per trade, per cluster, totaal)
- Probability modes slim opgezet (rule-based / LLM / hybrid)
- Dry-run first: professioneel

## Wat nog kwetsbaar is

- Confidence waarschijnlijk te simplistisch (één scalar pakt te veel samen)
- Thresholds nog niet empirisch gekalibreerd
- Exit logic ontbreekt nog volledig
- Replay/audit ontbreekt nog
- Cluster risk kan onderschat worden
- LLM-validatie moet systematischer

---

## Required Fixes

### A. Edge Drempels — 3 Banden

Huidige regels (`raw_edge >= 0.05`, `net_edge >= 0.03`) zijn goed voor launch, maar te grof voor schaalfase.

| Band | Raw Edge | Net Edge | Actie |
|---|---|---|---|
| **A — Strong** | >= 8% | >= 5% | Full size trade |
| **B — Normal** | >= 5% | >= 3% | Reduced size trade |
| **C — Observe** | 3-5% | < 3% | Alleen loggen, niet traden |

Band C is cruciaal: hiermee zie je later of je geld laat liggen of rotzooi vermijdt.

### B. Position Sizing — Twee Fasen

**Fase A — First money live (nu):**

| Parameter | Waarde |
|---|---|
| max_position_pct | 1.0% |
| max_cluster_pct | 3.0% |
| max_total_exposure_pct | 10.0% |
| max_daily_loss_pct | 2.5% |
| equity_kill_switch_pct | 10% |

**Fase B — Na 200+ trades met bewezen edge:**

| Parameter | Waarde |
|---|---|
| max_position_pct | 1.5-2.0% |
| max_cluster_pct | 5.0% |
| max_total_exposure_pct | 15-20% |
| max_daily_loss_pct | 5.0% |
| equity_kill_switch_pct | 15% |

Reden: sizing moet niet alleen marktrisico dragen, maar ook modelinterpretatierisico.

### C. Uncertainty Penalty — Later Decomponeren

Huidige formule is oké als MVP:
```
uncertainty_penalty = (1 - confidence) * 0.5 * raw_edge
```

Latere verbetering — confidence decomposition:
- `source_conf` — betrouwbaarheid bron
- `mapping_conf` — zekerheid markt-mapping
- `resolution_conf` — zekerheid resolutie-interpretatie
- `probability_conf` — zekerheid kansschatting
- `execution_conf` — zekerheid executiekwaliteit

Regime-based penalty (vervangt lineaire formule):

| Confidence | Penalty |
|---|---|
| >= 0.80 | 10% van raw edge |
| 0.65-0.80 | 25% van raw edge |
| 0.50-0.65 | 45% van raw edge |
| < 0.50 | **Hard veto** |

### D. Kelly Criterion — Niet Nu

Pas na voldoende trade history:
- Fractional Kelly (0.1-0.25 cap) op empirische edge per setup bucket
- Nooit uncapped Kelly

### E. 8 Extra Guardrails

| # | Guardrail | Beschrijving |
|---|---|---|
| 1 | **Cooldown per event** | Geen re-entry binnen X min op zelfde event, tenzij hogere source tier |
| 2 | **Novelty check** | Geen trade als headline herhaling is van al verwerkt nieuws |
| 3 | **Source escalation** | Tier-4 bron mag nooit zelfstandig executie triggeren |
| 4 | **Resolution ambiguity veto** | Hard veto als ambiguity boven drempel |
| 5 | **Market age / time-to-resolution** | Geen nieuwe trades vlak voor resolution, tenzij officieel + hoge confidence |
| 6 | **Orderbook shock filter** | Niet traden als spread/price net extreem bewoog |
| 7 | **Duplicate cluster thesis** | Niet 3 markten openen met feitelijk zelfde risico |
| 8 | **Model disagreement** | Als rule-based en LLM sterk verschillen: downgrade confidence of hard review |

### F. LLM Validatie — Shadow A/B

**Laag 1 — Shadow mode:** Beide engines draaien altijd, één beslist, rest logt mee.

**Laag 2 — Bucket evaluatie:** Groepeer per raw_edge, confidence, source_tier, category, time-to-resolution. Meet: hit rate, repricing capture, false positive rate, calibration error.

**Laag 3 — Counterfactual replay:** Historische events herspelen met alle drie modes.

LLM krijgt pas meer kapitaal als het op paper/replay beter scoort op:
- Hogere average net edge realized
- Lagere false positive rate
- Vergelijkbare of betere calibration
- Geen explosie in trade count
- Geen slechtere cluster concentration

---

## Bouwvolgorde

| Sprint | Wat | Waarom |
|---|---|---|
| **1** | Position Monitor + Exit Logic | Entry zonder exit = blind vliegen |
| **2** | Decision Audit + Replay | Meten is weten, zonder data geen calibratie |
| **3** | Kalibreer thresholds op buckets | Niet op gevoel, maar op empirische data |
| **4** | Pas sizing aan | Niet eerder dan na calibratie |

---

## Eindconclusie

Dit systeem is ver genoeg om serieus behandeld te worden als proto-trading desk infrastructure.
De juiste lagen zijn er. Nu begint het punt waar de meeste hobbybouwers afhaken:
niet meer bouwen, maar **meten, kalibreren en beperken**.

Precies daar wordt een echte quant machine geboren.
