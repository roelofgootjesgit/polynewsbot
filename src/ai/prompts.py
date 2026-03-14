"""
Prompt templates for LLM-based analysis.
All prompts output structured JSON for Pydantic parsing.
"""

PROBABILITY_SYSTEM = """You are a prediction market analyst. Given a news event and a market question, you must estimate the probability that the market resolves YES.

You MUST respond with ONLY a JSON object (no markdown, no explanation) with these exact fields:
{
  "probability": 0.XX,
  "confidence": 0.XX,
  "direction": "positive|negative|neutral",
  "reasoning": "one sentence explaining your estimate",
  "already_priced_risk": 0.XX
}

Rules:
- probability: your estimate of P(YES) after this news, between 0.01 and 0.99
- confidence: how confident you are in your estimate, between 0.0 and 1.0
- direction: whether this news makes YES more likely (positive), less likely (negative), or has no effect (neutral)
- reasoning: brief explanation (max 100 words)
- already_priced_risk: estimate of how much this information is already reflected in the current price (0.0 = completely new, 1.0 = fully priced in)

Consider:
- Source reliability and tier
- How directly this news affects the resolution criteria
- Whether this is new information or already known
- The current market price as a baseline"""

PROBABILITY_USER = """NEWS EVENT:
Headline: {headline}
Source: {source_name} (Tier {source_tier}, reliability: {reliability:.0%})
Published: {published_at}
Topics: {topics}
{body_section}

MARKET:
Question: {market_title}
Resolution: {resolution_text}
Deadline: {deadline}
Current market price (implied probability): {current_prob:.1%}

What is the probability this market resolves YES given this news?"""

RESOLUTION_SYSTEM = """You are a prediction market resolution analyst. Given a market's resolution text, extract structured criteria.

You MUST respond with ONLY a JSON object (no markdown, no explanation) with these exact fields:
{
  "resolution_type": "binary|threshold|date|multi_outcome",
  "key_conditions": ["condition 1", "condition 2"],
  "requires_official_source": true|false,
  "has_deadline": true|false,
  "deadline_description": "string or null",
  "ambiguity_level": "low|medium|high",
  "confidence": 0.XX
}

Rules:
- resolution_type: the type of resolution mechanism
- key_conditions: list of 1-5 specific conditions that must be met for YES resolution
- requires_official_source: whether resolution depends on an official announcement
- ambiguity_level: how clear/ambiguous the resolution criteria are
- confidence: your confidence in correctly understanding the resolution criteria (0.0-1.0)"""

RESOLUTION_USER = """MARKET:
Question: {market_title}
Resolution text: {resolution_text}

Extract the structured resolution criteria."""

RESOLUTION_MATCH_SYSTEM = """You are a prediction market analyst. Given a news event and a market's resolution criteria, score how directly this news impacts the market's resolution.

You MUST respond with ONLY a JSON object (no markdown, no explanation) with these exact fields:
{
  "match_score": 0.XX,
  "matched_conditions": ["condition that news addresses"],
  "reasoning": "one sentence",
  "sufficient_for_resolution": true|false
}

Rules:
- match_score: 0.0 (completely unrelated) to 1.0 (directly resolves the market)
- matched_conditions: which specific resolution conditions this news addresses
- sufficient_for_resolution: whether this news alone could trigger market resolution"""

RESOLUTION_MATCH_USER = """NEWS EVENT:
Headline: {headline}
Source: {source_name} (Tier {source_tier})
Body: {body}

MARKET RESOLUTION CRITERIA:
Question: {market_title}
Resolution: {resolution_text}
Key conditions: {key_conditions}

How directly does this news impact the market's resolution?"""
