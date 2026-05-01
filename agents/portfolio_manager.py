"""Portfolio Manager — final decision with portfolio context and history."""
from schemas import TradeProposal, RiskReview, FinalDecision
from agents.analysts.base import call_llm


SYSTEM = """You are the Portfolio Manager of an IDX equity fund.
You make final execution decisions considering: risk review, portfolio concentration, market conditions, and trade history.
Be decisive but prudent. If risk is too high, PASS or MONITOR.
Output JSON FinalDecision: ticker, decision (EXECUTE/PASS/MONITOR), action, quantity, entry_price, target_price, stop_loss, position_size_pct, reasoning, portfolio_context."""


def decide(proposal: TradeProposal, risk: RiskReview,
           memory_context: str = "", portfolio_value: float = 100_000_000) -> FinalDecision:

    user = f"""Make final decision for {proposal.ticker}:

TRADE PROPOSAL:
Action: {proposal.action.value}
Entry: Rp{proposal.entry_price:,.0f} | Target: Rp{proposal.target_price:,.0f} | Stop: Rp{proposal.stop_loss:,.0f}
Quantity: {proposal.quantity:,} | Hold: {proposal.hold_period}
Rationale: {proposal.rationale}

RISK REVIEW:
Approved: {risk.approved} | Risk level: {risk.risk_level.value}
Position size: {risk.position_size_pct:.1f}% | Max loss: {risk.max_loss_pct:.1f}%
Flags: {risk.risk_flags}
Adjustments: {risk.adjustments or 'None'}

PORTFOLIO HISTORY & CONTEXT:
{memory_context if memory_context else 'No prior positions. Fresh start.'}

Portfolio value: Rp{portfolio_value:,.0f}

Make your FINAL DECISION. Output FinalDecision JSON."""

    result = call_llm(SYSTEM, user, FinalDecision)
    result["ticker"] = proposal.ticker
    return FinalDecision(**result)
