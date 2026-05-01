"""Base analyst with shared LLM client."""
import os
import anthropic

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL  = "claude-haiku-4-5-20251001"


def _flatten(val):
    """Flatten a value to string if it's a dict."""
    if isinstance(val, dict):
        return " | ".join(str(v) for v in val.values() if v)
    return val


def _normalize_report(d: dict) -> dict:
    """Ensure correct types for all AnalystReport fields."""
    # Normalize signal / action enums
    _signal_map = {
        "NEUTRAL": "HOLD", "NEUTRAL_HOLD": "HOLD", "NO_POSITION": "HOLD",
        "HOLD_NO_POSITION": "HOLD", "PASS": "HOLD",
        "STRONG BUY": "STRONG_BUY", "STRONG SELL": "STRONG_SELL",
        "MODERATE BUY": "BUY", "MODERATE SELL": "SELL",
        "CAUTIOUS BUY": "BUY", "CAUTIOUS SELL": "SELL",
        "WEAK BUY": "BUY", "WEAK SELL": "SELL",
    }
    _valid_signals = {"STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL"}
    for field in ("signal", "action"):
        if field in d and isinstance(d[field], str):
            val = d[field].strip().upper().replace(" ", "_")
            val = _signal_map.get(val, val)
            d[field] = val if val in _valid_signals else ("HOLD" if field == "signal" else None)
        elif field == "action" and d.get(field) is None:
            pass  # Optional field, keep as None

    # Normalize risk_level
    _risk_map = {
        "CRITICAL": "REJECT", "EXTREME": "REJECT", "VERY_HIGH": "HIGH",
        "VERY HIGH": "HIGH", "LOW_RISK": "LOW", "MEDIUM_RISK": "MEDIUM",
        "HIGH_RISK": "HIGH", "MODERATE": "MEDIUM",
    }
    _valid_risks = {"LOW", "MEDIUM", "HIGH", "REJECT"}
    if "risk_level" in d and isinstance(d["risk_level"], str):
        val = d["risk_level"].strip().upper().replace(" ", "_")
        d["risk_level"] = _risk_map.get(val, val if val in _valid_risks else "HIGH")

    # Normalize string fields that LLM might return as dict/list
    for str_field in ("adjustments", "portfolio_context", "reasoning", "rationale", "summary"):
        if str_field in d:
            val = d[str_field]
            if isinstance(val, list):
                d[str_field] = " | ".join(str(x) for x in val)
            elif isinstance(val, dict):
                d[str_field] = " | ".join(f"{k}: {v}" for k, v in val.items())

    # Normalize decision to uppercase
    if "decision" in d and isinstance(d["decision"], str):
        d["decision"] = d["decision"].strip().upper()

    # Normalize confidence: 72 → 0.72
    if "confidence" in d and isinstance(d["confidence"], (int, float)):
        if d["confidence"] > 1.0:
            d["confidence"] = d["confidence"] / 100.0
        d["confidence"] = max(0.0, min(1.0, d["confidence"]))
    for field in ("key_points", "risks"):
        if field in d and isinstance(d[field], list):
            d[field] = [_flatten(item) if isinstance(item, dict) else str(item)
                        for item in d[field]]
    if "price_target" in d:
        pt = d["price_target"]
        if isinstance(pt, dict):
            # Take first numeric value found
            for v in pt.values():
                if isinstance(v, (int, float)):
                    d["price_target"] = float(v)
                    break
            else:
                d["price_target"] = None
        elif pt is not None:
            try:
                d["price_target"] = float(pt)
            except (TypeError, ValueError):
                d["price_target"] = None
    return d


def call_llm(system: str, user: str, schema_class) -> dict:
    """Call Claude with structured JSON output."""
    import json
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system + "\n\nRespond ONLY with valid JSON. key_points and risks must be list of plain strings. price_target must be a single number. No markdown.",
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    result = json.loads(text.strip())
    # Unwrap if LLM wraps in a schema key e.g. {"RiskReview": {...}}
    if len(result) == 1:
        inner = list(result.values())[0]
        if isinstance(inner, dict):
            result = inner
    return _normalize_report(result)
