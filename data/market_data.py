"""Market data fetcher for IDX stocks using yfinance."""
import asyncio
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from schemas import MarketData


def _to_jk(ticker: str) -> str:
    """Convert IDX ticker to Yahoo Finance format (e.g. BBCA -> BBCA.JK)."""
    t = ticker.upper().replace(".JK", "")
    return f"{t}.JK"


def fetch_market_data(ticker: str) -> MarketData:
    """Fetch comprehensive market data for an IDX stock."""
    sym = _to_jk(ticker)
    stock = yf.Ticker(sym)

    info = stock.info or {}
    hist = stock.history(period="1y")

    price         = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    change_pct    = info.get("regularMarketChangePercent", 0) or 0
    volume        = int(info.get("regularMarketVolume", 0) or 0)
    avg_vol_10d   = int(info.get("averageDailyVolume10Day", 0) or 0)

    # 52-week high/low
    high_52w = info.get("fiftyTwoWeekHigh")
    low_52w  = info.get("fiftyTwoWeekLow")

    # Fundamentals
    pe       = info.get("trailingPE")
    pb       = info.get("priceToBook")
    mktcap   = info.get("marketCap")
    rev_gr   = info.get("revenueGrowth")
    roe      = info.get("returnOnEquity")
    de       = info.get("debtToEquity")
    sector   = info.get("sector")

    # Technicals from history
    rsi_14 = macd_val = macd_sig = sma_50 = sma_200 = None
    if not hist.empty and len(hist) > 14:
        close = hist["Close"]
        # RSI
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss
        rsi_14 = float(round(100 - (100 / (1 + rs.iloc[-1])), 2))
        # MACD
        ema12  = close.ewm(span=12).mean()
        ema26  = close.ewm(span=26).mean()
        macd_line   = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        macd_val = float(round(macd_line.iloc[-1], 4))
        macd_sig = float(round(signal_line.iloc[-1], 4))
        # SMAs
        if len(close) >= 50:
            sma_50 = float(round(close.rolling(50).mean().iloc[-1], 2))
        if len(close) >= 200:
            sma_200 = float(round(close.rolling(200).mean().iloc[-1], 2))

    return MarketData(
        ticker=ticker.upper(),
        price=float(price),
        change_pct=float(change_pct),
        volume=volume,
        avg_vol_10d=avg_vol_10d,
        high_52w=high_52w,
        low_52w=low_52w,
        pe_ratio=pe,
        pb_ratio=pb,
        market_cap=mktcap,
        revenue_growth=rev_gr,
        roe=roe,
        debt_equity=de,
        rsi_14=rsi_14,
        macd=macd_val,
        macd_signal=macd_sig,
        sma_50=sma_50,
        sma_200=sma_200,
        sector=sector,
    )


async def fetch_market_data_async(ticker: str) -> MarketData:
    return await asyncio.get_event_loop().run_in_executor(None, fetch_market_data, ticker)
