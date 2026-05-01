"""Markdown logging + LLM reflection for memory injection."""
import os
from datetime import datetime
from pathlib import Path
from schemas import GraphState
from agents.analysts.base import client, MODEL

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def log_run(state: GraphState) -> str:
    """Save run to markdown log, return file path."""
    fd = state.final_decision
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = LOG_DIR / f"{state.ticker}_{ts}.md"

    lines = [
        f"# {state.ticker} — Run {state.run_id}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M WIB')}",
        "",
        "## Analyst Signals",
    ]
    for r in state.analyst_reports:
        lines.append(f"- **{r.analyst_type.upper()}**: {r.signal.value} ({r.confidence:.0%}) — {r.summary}")

    if state.debate_result:
        d = state.debate_result
        lines += ["", "## Debate", f"Winner: {d.winner} | Consensus: {d.consensus.value} ({d.confidence:.0%})", d.summary]

    if state.trade_proposal:
        p = state.trade_proposal
        lines += ["", "## Trade Proposal",
                  f"Action: **{p.action.value}** | Entry: Rp{p.entry_price:,.0f} | Target: Rp{p.target_price:,.0f} | Stop: Rp{p.stop_loss:,.0f}",
                  f"Qty: {p.quantity:,} | Hold: {p.hold_period}"]

    if state.risk_review:
        rr = state.risk_review
        lines += ["", "## Risk Review",
                  f"Approved: {rr.approved} | Level: {rr.risk_level.value} | Size: {rr.position_size_pct:.1f}%",
                  "Flags: " + (", ".join(rr.risk_flags) or "None")]

    if fd:
        lines += ["", "## FINAL DECISION",
                  f"**{fd.decision}** — {fd.reasoning}",
                  f"Portfolio context: {fd.portfolio_context}"]

    fname.write_text("\n".join(lines))
    return str(fname)


def load_recent_memory(ticker: str, n: int = 5) -> str:
    """Load last N runs for this ticker as memory context."""
    logs = sorted(LOG_DIR.glob(f"{ticker}_*.md"), reverse=True)[:n]
    if not logs:
        return ""
    parts = []
    for log in logs:
        parts.append(f"--- Previous run: {log.stem} ---\n{log.read_text()}")
    return "\n\n".join(parts)


def reflect(memory_context: str, ticker: str) -> str:
    """LLM reflection on past runs — extract lessons for current run."""
    if not memory_context:
        return ""
    resp = client.messages.create(
        model=MODEL, max_tokens=300,
        messages=[{"role": "user", "content": f"""Summarize key lessons from these past trades on {ticker}:

{memory_context}

In 3-5 bullet points, what patterns or mistakes should inform the next decision?"""}]
    )
    return resp.content[0].text.strip()
