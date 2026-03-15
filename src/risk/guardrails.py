"""
Guardrails — independent veto layer that can block any trade.
Stands between the edge engine and execution. Cannot be overridden by AI.
"""
import logging
import time
from typing import Any

from src.models.events import SourceTier
from src.models.markets import MarketState
from src.models.probability import ProbabilityAssessment
from src.models.trades import TradeDecision
from src.risk.exposure import ExposureTracker
from src.risk.sizing import PositionSizer

logger = logging.getLogger(__name__)


class GuardrailResult:
    __slots__ = ("approved", "veto_reasons", "position_size_usd")

    def __init__(self):
        self.approved: bool = True
        self.veto_reasons: list[str] = []
        self.position_size_usd: float = 0.0


class Guardrails:
    """
    Veto logic — independent of the intelligence layer.
    A good bot is defined by how often it correctly does NOT trade.

    Checks (quant-approved):
    - Edge band must allow execution
    - Source quality minimum
    - Confidence minimum (hard veto < 0.5)
    - Spread maximum
    - Liquidity quality
    - Resolution match strength
    - Daily loss circuit breaker
    - Equity kill switch (drawdown from peak)
    - Event cooldown (no re-entry same event within window)
    - Source escalation (tier 4 alone cannot trigger)
    - Size scale from edge band applied to position sizing
    """

    def __init__(self, cfg: dict[str, Any]):
        risk_cfg = cfg.get("risk", {})
        self.min_source_tier: int = risk_cfg.get("min_source_tier", 3)
        self.min_confidence: float = risk_cfg.get("min_confidence", 0.5)
        self.max_spread: float = risk_cfg.get("max_spread", 0.10)
        self.max_daily_loss_pct: float = risk_cfg.get("max_daily_loss_pct", 0.025)
        self.equity_kill_switch: float = risk_cfg.get("equity_kill_switch_pct", 0.10)
        self.event_cooldown_minutes: float = risk_cfg.get("event_cooldown_minutes", 30)

        self._sizer = PositionSizer(cfg)
        self._daily_pnl: float = 0.0
        self._peak_capital: float = 0.0
        self._kill_switch: bool = False

        self._event_last_trade: dict[str, float] = {}

    def evaluate(
        self,
        decision: TradeDecision,
        assessment: ProbabilityAssessment,
        market_state: MarketState,
        exposure: ExposureTracker,
        capital: float,
        cluster_id: str | None = None,
    ) -> GuardrailResult:
        """Run all guardrail checks. Returns approval + sizing."""
        result = GuardrailResult()

        if self._kill_switch:
            result.approved = False
            result.veto_reasons.append("equity kill switch active")
            return result

        if not decision.execution_allowed:
            result.approved = False
            result.veto_reasons.extend(decision.veto_reasons)
            return result

        # --- Source quality check ---
        if assessment.source_quality_score < 0.3:
            result.veto_reasons.append(
                f"source quality {assessment.source_quality_score:.2f} too low"
            )

        # --- Source escalation: tier 4 alone cannot trigger ---
        if (hasattr(assessment, 'source_quality_score')
                and assessment.source_quality_score <= 0.25
                and decision.confidence < 0.7):
            result.veto_reasons.append("tier 4 source cannot trigger alone")

        # --- Confidence check ---
        if decision.confidence < self.min_confidence:
            result.veto_reasons.append(
                f"confidence {decision.confidence:.2f} < {self.min_confidence}"
            )

        # --- Spread check ---
        if market_state.spread and market_state.spread > self.max_spread:
            result.veto_reasons.append(
                f"spread {market_state.spread:.4f} > {self.max_spread}"
            )

        # --- Liquidity check ---
        if market_state.liquidity_quality == "low":
            result.veto_reasons.append("liquidity quality is low")

        # --- Resolution uncertainty ---
        if assessment.resolution_match_score < 0.3:
            result.veto_reasons.append(
                f"resolution match {assessment.resolution_match_score:.2f} too weak"
            )

        # --- Daily loss circuit breaker ---
        if capital > 0 and self._daily_pnl / capital <= -self.max_daily_loss_pct:
            result.veto_reasons.append("daily loss limit reached")

        # --- Event cooldown ---
        event_id = decision.event_id
        last_trade_time = self._event_last_trade.get(event_id)
        if last_trade_time:
            elapsed_min = (time.time() - last_trade_time) / 60.0
            if elapsed_min < self.event_cooldown_minutes:
                result.veto_reasons.append(
                    f"event cooldown: {elapsed_min:.0f}min < {self.event_cooldown_minutes}min"
                )

        # --- Position sizing (also checks exposure limits) ---
        if not result.veto_reasons:
            cluster_exp = exposure.get_cluster_exposure(cluster_id)
            total_exp = exposure.get_total_exposure()
            price = market_state.best_ask or market_state.mid_price or 0.5

            size = self._sizer.calculate(
                capital=capital,
                price=price,
                confidence=decision.confidence,
                cluster_exposure=cluster_exp,
                total_exposure=total_exp,
            )

            size *= decision.size_scale

            if size <= 0:
                result.veto_reasons.append("position size is zero (exposure limits)")
            else:
                result.position_size_usd = round(size, 2)

        result.approved = len(result.veto_reasons) == 0

        if result.approved:
            self._event_last_trade[event_id] = time.time()
            logger.info(
                "APPROVED: %s %s | band=%s | edge=%.4f | size=$%.2f | %s",
                decision.side, decision.market_id[:16],
                decision.edge_band, decision.net_edge,
                result.position_size_usd,
                assessment.reasoning_summary[:60],
            )
        else:
            logger.info(
                "VETOED: %s %s | reasons: %s",
                decision.side, decision.market_id[:16],
                "; ".join(result.veto_reasons),
            )

        return result

    def update_daily_pnl(self, pnl_change: float) -> None:
        self._daily_pnl += pnl_change

    def reset_daily(self) -> None:
        self._daily_pnl = 0.0

    def check_kill_switch(self, capital: float, initial_capital: float) -> bool:
        """Check if drawdown from peak triggers the kill switch."""
        self._peak_capital = max(self._peak_capital, capital)
        if self._peak_capital > 0:
            dd = (self._peak_capital - capital) / self._peak_capital
            if dd >= self.equity_kill_switch:
                self._kill_switch = True
                logger.warning("KILL SWITCH: drawdown %.2f%% from peak", dd * 100)
        return self._kill_switch
