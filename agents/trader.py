"""Trader agent — generates trade proposal from debate + analyst signals."""
from schemas import AnalystReport, DebateResult, MarketData, TradeProposal, Signal
from agents.analysts.base import call_llm


SYSTEM = """You are an experienced equity trader for IDX stocks.
Given analyst reports and debate outcome, generate a specific trade proposal.
Be precise with numbers. Entry near current price, target based on analysis, stop-loss for risk management.
Output JSON TradeProposal: ticker, action, quantity, entry_price, target_price, stop_loss, hold_period, rationale, analyst_signals, debate_outcome."""


def propose(data: MarketData, reports: list[AnalystReport], debate: DebateResult,
            portfolio_value: float = 100_000_000) -> TradeProposal:
    signals_str = " | ".join(f"{r.analyst_type}: {r.signal.value} ({r.confidence:.0%})" for r in reports)
    max_position = portfolio_value * 0.10  # max 10% per trade
    suggested_qty = int(max_position / data.price) if data.price > 0 else 0

    user = f"""Generate trade proposal for {data.ticker}:

Current price: Rp{data.price:,.0f}
Analyst signals: {signals_str}
Debate consensus: {debate.consensus.value} (confidence: {debate.confidence:.0%})
Debate winner: {debate.winner}

Portfolio value: Rp{portfolio_value:,.0f}
Max position size: Rp{max_position:,.0f} (10%)
Suggested max qty: {suggested_qty:,} shares

Key analyst insight: {reports[0].summary if reports else 'N/A'}

Generate TradeProposal JSON."""

    result = call_llm(SYSTEM, user, TradeProposal)
    result["ticker"]          = data.ticker
    result["analyst_signals"] = [r.signal for r in reports]
    result["debate_outcome"]  = debate.consensus
    return TradeProposal(**result)
