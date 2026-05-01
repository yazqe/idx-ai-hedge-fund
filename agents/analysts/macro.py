"""Macro analyst — IDX market context, sector rotation, economic conditions."""
from schemas import MarketData, AnalystReport
from agents.analysts.base import call_llm


SYSTEM = """You are a macro analyst specializing in Indonesian economy and IDX market.
Evaluate stocks in the context of: Bank Indonesia policy, USD/IDR, commodity prices (coal, palm oil, nickel),
government infrastructure spending, inflation, and global risk-on/risk-off conditions.
Output a JSON AnalystReport with fields: analyst_type, ticker, signal, confidence, summary, key_points, risks."""

# Static macro context — can be updated daily via scraper
MACRO_CONTEXT = """Current IDX macro environment:
- Bank Indonesia benchmark rate: 6.0%
- USD/IDR: ~16,400
- IHSG YTD: -4.7% (April 2026)
- Key drivers: commodity prices, asing (foreign) flow, global risk sentiment
- Sector rotation: mining/energy under pressure, consumer & tech selective strength
- Indonesia GDP growth: ~5.0% target
"""


def analyze(data: MarketData) -> AnalystReport:
    user = f"""Analyze {data.ticker} in macro context:
Sector: {data.sector}
Market Cap: {data.market_cap}
Price performance: {data.change_pct:+.2f}% daily

{MACRO_CONTEXT}

How does macro environment affect {data.ticker}?
Generate a macro AnalystReport JSON."""

    result = call_llm(SYSTEM, user, AnalystReport)
    result["analyst_type"] = "macro"
    result["ticker"] = data.ticker
    result.pop("price_target", None)
    return AnalystReport(**result)


async def analyze_async(data: MarketData) -> AnalystReport:
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, analyze, data)
