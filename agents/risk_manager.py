"""Risk Manager — rules-based + LLM review of trade proposals."""
from schemas import TradeProposal, MarketData, RiskReview, RiskLevel
from agents.analysts.base import call_llm


SYSTEM = """You are a risk manager for an IDX equity fund.
Apply both quantitative rules AND qualitative judgment.
Rules:
- Max position: 10% of portfolio
- Min risk/reward ratio: 1.5x
- Max drawdown tolerance: 8%
- Avoid stocks with debt/equity > 3.0
- Flag low-liquidity stocks (volume < 5M shares/day)
Output JSON RiskReview: ticker, approved, risk_level, position_size_pct, max_loss_pct, risk_flags, adjustments."""


def review(proposal: TradeProposal, data: MarketData,
           portfolio_value: float = 100_000_000) -> RiskReview:

    # Quantitative checks
    flags = []
    position_value = proposal.quantity * proposal.entry_price
    position_pct   = position_value / portfolio_value * 100

    rr_ratio = (proposal.target_price - proposal.entry_price) / max(
        proposal.entry_price - proposal.stop_loss, 1)

    if position_pct > 10:
        flags.append(f"Position size {position_pct:.1f}% exceeds 10% limit")
    if rr_ratio < 1.5:
        flags.append(f"R/R ratio {rr_ratio:.2f}x below 1.5x minimum")
    if data.volume < 5_000_000:
        flags.append(f"Low liquidity: volume {data.volume:,} < 5M daily")
    if data.debt_equity and data.debt_equity > 3.0:
        flags.append(f"High leverage: D/E ratio {data.debt_equity:.1f}")
    if data.rsi_14 and data.rsi_14 > 75:
        flags.append(f"Overbought: RSI {data.rsi_14:.0f} > 75")

    user = f"""Review trade proposal for {proposal.ticker}:

Action: {proposal.action.value}
Entry: Rp{proposal.entry_price:,.0f} | Target: Rp{proposal.target_price:,.0f} | Stop: Rp{proposal.stop_loss:,.0f}
Quantity: {proposal.quantity:,} shares
Position value: Rp{position_value:,.0f} ({position_pct:.1f}% of portfolio)
R/R ratio: {rr_ratio:.2f}x
Hold period: {proposal.hold_period}

Quantitative flags: {flags if flags else 'None'}

Market data:
- Volume: {data.volume:,} | Avg10D: {data.avg_vol_10d}
- RSI: {data.rsi_14} | D/E: {data.debt_equity}
- Sector: {data.sector}

Provide risk assessment and adjustments if needed. Output RiskReview JSON."""

    result = call_llm(SYSTEM, user, RiskReview)
    result["ticker"] = proposal.ticker
    if "risk_flags" not in result:
        result["risk_flags"] = flags
    return RiskReview(**result)
