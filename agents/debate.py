"""Bull vs Bear debate loop — configurable rounds."""
import json
from schemas import AnalystReport, DebateMessage, DebateResult, Signal, Stance
from agents.analysts.base import call_llm, client, MODEL


BULL_SYSTEM = """You are a BULL investor debating why to BUY this stock.
Use analyst reports as evidence. Be specific with numbers. Counter bear arguments sharply.
Output JSON: {round, stance, argument, evidence: [], rebuttal: "..."}"""

BEAR_SYSTEM = """You are a BEAR investor debating why to SELL/AVOID this stock.
Use analyst reports as evidence. Be specific with numbers. Counter bull arguments sharply.
Output JSON: {round, stance, argument, evidence: [], rebuttal: "..."}"""


def _analyst_summary(reports: list[AnalystReport]) -> str:
    lines = []
    for r in reports:
        lines.append(f"[{r.analyst_type.upper()}] Signal: {r.signal.value} | Confidence: {r.confidence:.0%}")
        lines.append(f"  Summary: {r.summary}")
    return "\n".join(lines)


def run_debate(ticker: str, reports: list[AnalystReport], rounds: int = 2) -> DebateResult:
    """Run N-round bull/bear debate, return structured result."""
    analyst_ctx = _analyst_summary(reports)
    messages: list[DebateMessage] = []
    last_bull = last_bear = ""

    for rnd in range(1, rounds + 1):
        # Bull turn
        bull_prompt = f"""Ticker: {ticker} | Round {rnd}
Analyst reports:
{analyst_ctx}

{'Bear said: ' + last_bear if last_bear else 'Start your bull case.'}

Make your BULL argument for round {rnd}."""
        bull_raw = call_llm(BULL_SYSTEM, bull_prompt, DebateMessage)
        bull_raw.update({"round": rnd, "stance": "BULL"})
        bull_msg = DebateMessage(**bull_raw)
        messages.append(bull_msg)
        last_bull = bull_msg.argument

        # Bear turn
        bear_prompt = f"""Ticker: {ticker} | Round {rnd}
Analyst reports:
{analyst_ctx}

Bull said: {last_bull}

Make your BEAR argument for round {rnd}."""
        bear_raw = call_llm(BEAR_SYSTEM, bear_prompt, DebateMessage)
        bear_raw.update({"round": rnd, "stance": "BEAR"})
        bear_msg = DebateMessage(**bear_raw)
        messages.append(bear_msg)
        last_bear = bear_msg.argument

    # Determine winner & consensus
    bull_signals  = [r for r in reports if r.signal.value in ("STRONG_BUY", "BUY")]
    bear_signals  = [r for r in reports if r.signal.value in ("STRONG_SELL", "SELL")]
    avg_confidence = sum(r.confidence for r in reports) / len(reports)

    if len(bull_signals) > len(bear_signals):
        winner    = Stance.BULL
        consensus = Signal.BUY if avg_confidence < 0.75 else Signal.STRONG_BUY
    elif len(bear_signals) > len(bull_signals):
        winner    = Stance.BEAR
        consensus = Signal.SELL if avg_confidence < 0.75 else Signal.STRONG_SELL
    else:
        winner    = None
        consensus = Signal.HOLD

    # Summary via LLM
    summary_prompt = f"""Summarize this debate for {ticker} in 2 sentences:
Bull case: {last_bull}
Bear case: {last_bear}
Consensus: {consensus.value}"""
    summ_resp = client.messages.create(
        model=MODEL, max_tokens=200,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    summary = summ_resp.content[0].text.strip()

    return DebateResult(
        ticker=ticker,
        rounds=messages,
        winner=winner,
        consensus=consensus,
        confidence=avg_confidence,
        summary=summary,
    )
