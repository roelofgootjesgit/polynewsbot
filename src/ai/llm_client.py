"""
LLM client wrapper — handles OpenAI API calls with cost tracking,
retries, and timeout management.
"""
import json
import logging
import time
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMUsage(BaseModel):
    """Token usage for a single LLM call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model: str = ""
    latency_ms: float = 0.0


class LLMCostTracker:
    """Accumulates LLM costs across the session."""

    def __init__(self):
        self._calls: list[LLMUsage] = []

    def record(self, usage: LLMUsage) -> None:
        self._calls.append(usage)

    @property
    def total_calls(self) -> int:
        return len(self._calls)

    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self._calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(u.estimated_cost_usd for u in self._calls)

    def summary(self) -> str:
        return (
            f"LLM usage: {self.total_calls} calls, "
            f"{self.total_tokens} tokens, "
            f"${self.total_cost_usd:.4f}"
        )


_COST_PER_1K = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
    "gpt-4.1-nano": {"input": 0.0001, "output": 0.0004},
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PER_1K.get(model, {"input": 0.001, "output": 0.002})
    return (prompt_tokens / 1000 * rates["input"] +
            completion_tokens / 1000 * rates["output"])


class LLMClient:
    """Wrapper around OpenAI API with cost tracking and retries."""

    def __init__(self, cfg: dict[str, Any]):
        ai_cfg = cfg.get("ai", {})
        self.model: str = ai_cfg.get("model", "gpt-4o-mini")
        self.max_tokens: int = ai_cfg.get("max_tokens", 500)
        self.temperature: float = ai_cfg.get("temperature", 0.2)
        self.timeout: int = ai_cfg.get("timeout_seconds", 15)
        self.max_retries: int = ai_cfg.get("max_retries", 2)

        self._api_key: str = ai_cfg.get("openai_api_key", "")
        self._client = None
        self.cost_tracker = LLMCostTracker()
        self._available = False

    def connect(self) -> bool:
        """Initialize OpenAI client. Returns True if available."""
        if not self._api_key:
            logger.warning("No OpenAI API key configured — LLM features disabled")
            return False

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._api_key,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
            self._available = True
            logger.info("LLM client ready (model=%s)", self.model)
            return True
        except Exception:
            logger.exception("Failed to initialize OpenAI client")
            return False

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> tuple[str, LLMUsage]:
        """
        Send a chat completion request.
        Returns (response_text, usage).
        Raises RuntimeError if LLM is not available.
        """
        if not self.available:
            raise RuntimeError("LLM client not available")

        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        start = time.perf_counter()

        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        latency = (time.perf_counter() - start) * 1000

        text = response.choices[0].message.content or ""
        raw_usage = response.usage

        usage = LLMUsage(
            prompt_tokens=raw_usage.prompt_tokens if raw_usage else 0,
            completion_tokens=raw_usage.completion_tokens if raw_usage else 0,
            total_tokens=raw_usage.total_tokens if raw_usage else 0,
            estimated_cost_usd=_estimate_cost(
                model,
                raw_usage.prompt_tokens if raw_usage else 0,
                raw_usage.completion_tokens if raw_usage else 0,
            ),
            model=model,
            latency_ms=round(latency, 1),
        )
        self.cost_tracker.record(usage)

        logger.debug(
            "LLM call: %s, %d tokens, $%.4f, %.0fms",
            model, usage.total_tokens, usage.estimated_cost_usd, latency,
        )
        return text, usage

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> tuple[dict[str, Any], LLMUsage]:
        """Chat and parse response as JSON. Raises ValueError on parse failure."""
        text, usage = self.chat(system_prompt, user_prompt, **kwargs)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text), usage
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {text[:300]}") from e
