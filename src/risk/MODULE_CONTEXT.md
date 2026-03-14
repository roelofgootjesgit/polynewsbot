# Risk & Guardrails — MODULE_CONTEXT

## Wat
Veto-logica + position sizing + portfolio exposure. Staat los van de intelligentielaag.

## Bestanden
- `sizing.py` — PositionSizer: max % per trade, cluster, totaal + confidence scaling
- `exposure.py` — ExposureTracker: portfolio exposure per cluster en totaal
- `guardrails.py` — Guardrails: onafhankelijke veto checks + kill switch

## Interfaces
- **Input:** TradeDecision + ProbabilityAssessment + MarketState + ExposureTracker + capital
- **Output:** GuardrailResult (approved bool, veto_reasons, position_size_usd)

## Veto regels
- Source quality te laag (< 0.3)
- Confidence onder minimum
- Spread te breed
- Liquidity quality "low"
- Resolution match te zwak (< 0.3)
- Daily loss limit bereikt
- Equity kill switch (drawdown van peak)
- Position size = 0 door exposure limits

## Kill switch
- Tracked drawdown van peak capital
- Eenmaal geactiveerd blokkeert alle trades

## Config sectie: `risk.*` in default.yaml

## Status
- [x] Position sizing — Fase 4 compleet
- [x] Exposure tracker — Fase 4 compleet
- [x] Guardrails + kill switch — Fase 4 compleet
