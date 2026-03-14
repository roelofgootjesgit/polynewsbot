"""
Hybrid engine — tries LLM first, falls back to rule-based on failure.
Configurable via probability.method: "rule_based" | "llm" | "hybrid"
"""
import logging
from typing import Any, Optional

from src.ai.llm_client import LLMClient
from src.ai.llm_probability import LLMProbabilityEngine
from src.ai.llm_resolution import LLMResolutionParser
from src.models.events import NormalizedNewsEvent
from src.models.markets import MarketCandidate
from src.models.probability import ProbabilityAssessment
from src.probability.engine import ProbabilityEngine as RuleBasedProbability
from src.resolution.parser import (
    ResolutionCriteria,
    ResolutionMatch,
    ResolutionParser as RuleBasedResolution,
)

logger = logging.getLogger(__name__)


class HybridProbabilityEngine:
    """
    Probability engine with LLM + rule-based fallback.
    method=rule_based: only rules (no LLM calls)
    method=llm: only LLM (fails if unavailable)
    method=hybrid: try LLM, fallback to rules
    """

    def __init__(self, cfg: dict[str, Any], llm: Optional[LLMClient] = None):
        self._method = cfg.get("probability", {}).get("method", "rule_based")
        self._rule_engine = RuleBasedProbability(cfg)
        self._llm_engine: Optional[LLMProbabilityEngine] = None
        self._llm_failures = 0

        if llm and llm.available and self._method in ("llm", "hybrid"):
            self._llm_engine = LLMProbabilityEngine(llm)

    def assess(
        self,
        event: NormalizedNewsEvent,
        market: MarketCandidate,
        resolution_match: ResolutionMatch,
        current_market_prob: float,
    ) -> ProbabilityAssessment:
        if self._method == "rule_based" or not self._llm_engine:
            return self._rule_engine.assess(event, market, resolution_match, current_market_prob)

        if self._method == "llm":
            return self._llm_engine.assess(event, market, resolution_match, current_market_prob)

        # hybrid: try LLM, fallback to rules
        try:
            result = self._llm_engine.assess(event, market, resolution_match, current_market_prob)
            self._llm_failures = 0
            return result
        except Exception as e:
            self._llm_failures += 1
            logger.warning(
                "LLM probability failed (attempt #%d): %s — using rule-based fallback",
                self._llm_failures, str(e)[:100],
            )
            return self._rule_engine.assess(event, market, resolution_match, current_market_prob)

    @property
    def method(self) -> str:
        return self._method

    @property
    def llm_available(self) -> bool:
        return self._llm_engine is not None


class HybridResolutionParser:
    """
    Resolution parser with LLM + rule-based fallback.
    Uses LLM when available, falls back to regex rules.
    """

    def __init__(self, cfg: dict[str, Any], llm: Optional[LLMClient] = None):
        self._method = cfg.get("probability", {}).get("method", "rule_based")
        self._rule_parser = RuleBasedResolution(cfg)
        self._llm_parser: Optional[LLMResolutionParser] = None

        if llm and llm.available and self._method in ("llm", "hybrid"):
            self._llm_parser = LLMResolutionParser(llm)

    def parse_criteria(self, market: MarketCandidate) -> ResolutionCriteria:
        if self._method == "rule_based" or not self._llm_parser:
            return self._rule_parser.parse_criteria(market)

        try:
            return self._llm_parser.parse_criteria(market)
        except Exception as e:
            logger.warning("LLM resolution parse failed: %s — using rules", str(e)[:100])
            return self._rule_parser.parse_criteria(market)

    def match_event(
        self,
        event: NormalizedNewsEvent,
        criteria: ResolutionCriteria,
    ) -> ResolutionMatch:
        if self._method == "rule_based" or not self._llm_parser:
            return self._rule_parser.match_event(event, criteria)

        try:
            return self._llm_parser.match_event(event, criteria)
        except Exception as e:
            logger.warning("LLM resolution match failed: %s — using rules", str(e)[:100])
            return self._rule_parser.match_event(event, criteria)
