# AI / LLM Layer — MODULE_CONTEXT

## Wat
LLM-based interpretatie voor probability assessment en resolution understanding.
Graceful fallback naar rule-based bij fouten of geen API key.

## Bestanden
- `llm_client.py` — LLMClient wrapper met cost tracking, retries, JSON parsing
- `prompts.py` — Prompt templates voor probability + resolution analysis
- `llm_probability.py` — LLMProbabilityEngine: structured prompt -> ProbabilityAssessment
- `llm_resolution.py` — LLMResolutionParser: resolution text -> ResolutionCriteria + match score
- `hybrid.py` — HybridProbabilityEngine + HybridResolutionParser: LLM met rule-based fallback

## Interfaces
- **LLMClient.chat_json()** — system + user prompt -> parsed JSON dict
- **LLMCostTracker** — accumuleert tokens + kosten per sessie
- **HybridProbabilityEngine.assess()** — zelfde interface als ProbabilityEngine
- **HybridResolutionParser.parse_criteria() / match_event()** — zelfde interface als ResolutionParser

## Modes (probability.method in config)
- `rule_based` — geen LLM calls, puur keyword + sentiment
- `llm` — alleen LLM (faalt als key ontbreekt)
- `hybrid` — probeer LLM, fallback naar rules bij fout

## Config sectie: `ai.*` + `probability.method` in default.yaml
- `ai.openai_api_key` — of via env `OPENAI_API_KEY`
- `ai.model` — default "gpt-4o-mini"
- `ai.max_tokens`, `ai.temperature`, `ai.timeout_seconds`

## Cost tracking
- Elke LLM call wordt getrackt (tokens, cost, latency)
- Summary wordt gelogd bij pipeline shutdown

## Status
- [x] LLM client + cost tracking — Fase 6 compleet
- [x] LLM probability engine — Fase 6 compleet
- [x] LLM resolution parser — Fase 6 compleet
- [x] Hybrid engines met fallback — Fase 6 compleet
- [x] Pipeline integratie — Fase 6 compleet
- [x] 16 unit tests passing
