"""Fundamental analyst — valuasi, pertumbuhan, kualitas bisnis."""
from schemas import MarketData, AnalystReport, Signal
from agents.analysts.base import call_llm


SYSTEM = """You are a fundamental analyst specializing in Indonesian stocks (IDX).
Evaluate stocks based on valuation, growth, profitability and balance sheet quality.
Focus on: P/E ratio vs sector, P/B ratio, ROE, revenue growth, debt/equity.
For IDX context: consider Indonesian market conditions, regulatory environment, and sector dynamics.
Output a JSON AnalystReport with fields: analyst_type, ticker, signal, confidence, summary, key_points, risks, price_target."""


def analyze(data: MarketData) -> AnalystReport:
    user = f"""Analyze {data.ticker} fundamentals:
Price: Rp{data.price:,.0f}
P/E: {data.pe_ratio}
P/B: {data.pb_ratio}
ROE: {data.roe}
Revenue Growth: {data.revenue_growth}
Debt/Equity: {data.debt_equity}
Market Cap: {data.market_cap}
Sector: {data.sector}
52W High: {data.high_52w} | 52W Low: {data.low_52w}

Generate a fundamental AnalystReport JSON."""

    result = call_llm(SYSTEM, user, AnalystReport)
    result["analyst_type"] = "fundamental"
    result["ticker"] = data.ticker
    return AnalystReport(**result)


async def analyze_async(data: MarketData) -> AnalystReport:
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, analyze, data)
