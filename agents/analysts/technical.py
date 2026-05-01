"""Technical analyst — price action, momentum, trend."""
from schemas import MarketData, AnalystReport
from agents.analysts.base import call_llm


SYSTEM = """You are a technical analyst specializing in IDX stocks.
Evaluate based on: RSI, MACD, moving averages (SMA50/200), price relative to 52W range.
Identify trend direction, momentum signals, support/resistance levels.
Output a JSON AnalystReport with fields: analyst_type, ticker, signal, confidence, summary, key_points, risks, price_target."""


def analyze(data: MarketData) -> AnalystReport:
    price_vs_sma50  = f"{((data.price/data.sma_50 - 1)*100):.1f}% vs SMA50"  if data.sma_50  else "N/A"
    price_vs_sma200 = f"{((data.price/data.sma_200 - 1)*100):.1f}% vs SMA200" if data.sma_200 else "N/A"
    high_pct = f"{((data.price/data.high_52w - 1)*100):.1f}% from 52W High" if data.high_52w else "N/A"

    user = f"""Analyze {data.ticker} technicals:
Price: Rp{data.price:,.0f} | Change: {data.change_pct:+.2f}%
RSI(14): {data.rsi_14}
MACD: {data.macd} | Signal: {data.macd_signal}
SMA50: {data.sma_50} ({price_vs_sma50})
SMA200: {data.sma_200} ({price_vs_sma200})
52W Range: {data.low_52w} – {data.high_52w} ({high_pct})
Volume: {data.volume:,} | Avg10D: {data.avg_vol_10d:,}

Generate a technical AnalystReport JSON."""

    result = call_llm(SYSTEM, user, AnalystReport)
    result["analyst_type"] = "technical"
    result["ticker"] = data.ticker
    return AnalystReport(**result)


async def analyze_async(data: MarketData) -> AnalystReport:
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, analyze, data)
