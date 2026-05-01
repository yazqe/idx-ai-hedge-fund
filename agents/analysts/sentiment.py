"""Sentiment analyst — news, social media, market mood."""
import requests
from schemas import MarketData, AnalystReport
from agents.analysts.base import call_llm


SYSTEM = """You are a sentiment analyst for IDX Indonesian stocks.
Analyze market sentiment from news headlines, volume patterns, and price momentum.
Consider Indonesian market context: retail investor behavior, government announcements, commodity prices.
Output a JSON AnalystReport with fields: analyst_type, ticker, signal, confidence, summary, key_points, risks."""


def fetch_news_headlines(ticker: str) -> list[str]:
    """Fetch recent news via Yahoo Finance RSS."""
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}.JK&region=ID&lang=id-ID"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return []
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text)
        return [item.find("title").text for item in root.iter("item")][:10]
    except Exception:
        return []


def analyze(data: MarketData) -> AnalystReport:
    headlines = fetch_news_headlines(data.ticker)
    headlines_text = "\n".join(f"- {h}" for h in headlines) if headlines else "No recent news found."

    # Volume sentiment: relative volume as proxy for interest
    vol_ratio = data.volume / data.avg_vol_10d if data.avg_vol_10d else 1.0
    vol_sentiment = "HIGH interest" if vol_ratio > 2 else "NORMAL" if vol_ratio > 0.7 else "LOW interest"

    user = f"""Analyze sentiment for {data.ticker} (Sector: {data.sector}):

Price momentum: {data.change_pct:+.2f}%
Volume: {data.volume:,} ({vol_ratio:.1f}x avg) → {vol_sentiment}

Recent news headlines:
{headlines_text}

Assess market sentiment and generate a sentiment AnalystReport JSON."""

    result = call_llm(SYSTEM, user, AnalystReport)
    result["analyst_type"] = "sentiment"
    result["ticker"] = data.ticker
    result.pop("price_target", None)
    return AnalystReport(**result)


async def analyze_async(data: MarketData) -> AnalystReport:
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(None, analyze, data)
