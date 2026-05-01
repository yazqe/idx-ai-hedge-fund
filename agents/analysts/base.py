"""Base analyst with shared LLM client."""
import os
import anthropic
from schemas import MarketData, AnalystReport

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL  = "claude-haiku-4-5-20251001"


def call_llm(system: str, user: str, schema_class) -> dict:
    """Call Claude with structured JSON output."""
    import json
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system + "\n\nRespond ONLY with valid JSON matching the requested schema. No markdown, no explanation outside the JSON.",
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())
