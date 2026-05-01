"""Market data fetcher — datasectors API (primary) + yfinance (fundamentals/fallback)."""
import os
import asyncio
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from schemas import MarketData

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATASECTORS_HOST = "https://api.datasectors.com"
DATASECTORS_KEY  = os.environ.get("SECRET_TOKEN", "")


def _ds_headers():
    return {"X-API-Key": DATASECTORS_KEY, "Accept": "application/json"}


def _fetch_datasectors_ohlcv(ticker: str, days: int = 365) -> pd.DataFrame:
    """Fetch OHLCV from datasectors API. Returns normalized DataFrame."""
    end   = datetime.today()
    start = end - timedelta(days=days)
    url   = (
        f"{DATASECTORS_HOST}/api/chart-saham/{ticker.upper()}/daily"
        f"?from={start.strftime('%Y-%m-%d')}&to={end.strftime('%Y-%m-%d')}"
    )
    r = requests.get(url, headers=_ds_headers(), timeout=15)
    if r.status_code != 200:
        raise ValueError(f"datasectors HTTP {r.status_code}: {r.text[:100]}")

    raw = r.json()

    # Unwrap common envelope formats
    rows = None
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        for key in ("data", "candles", "ohlcv", "chart", "result", "prices", "bars"):
            if key in raw and isinstance(raw[key], list):
                rows = raw[key]
                break

    if not rows:
        raise ValueError(f"datasectors: unexpected response shape — {str(raw)[:120]}")

    df = pd.DataFrame(rows)

    # Normalize column names to standard Open/High/Low/Close/Volume
    rename = {}
    for col in df.columns:
        cl = col.lower()
        if cl in ("date", "time", "datetime", "timestamp", "t"):
            rename[col] = "Date"
        elif cl in ("open", "o"):
            rename[col] = "Open"
        elif cl in ("high", "h"):
            rename[col] = "High"
        elif cl in ("low", "l"):
            rename[col] = "Low"
        elif cl in ("close", "c", "last", "price"):
            rename[col] = "Close"
        elif cl in ("volume", "v", "vol"):
            rename[col] = "Volume"
    df = df.rename(columns=rename)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()

    for col in ("Open", "High", "Low", "Close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)

    return df


def _calc_technicals(hist: pd.DataFrame):
    """RSI-14, MACD, SMA-50, SMA-200 from OHLCV DataFrame."""
    rsi_14 = macd_val = macd_sig = sma_50 = sma_200 = None
    if hist.empty or "Close" not in hist.columns:
        return rsi_14, macd_val, macd_sig, sma_50, sma_200

    close = hist["Close"].dropna()
    if len(close) < 15:
        return rsi_14, macd_val, macd_sig, sma_50, sma_200

    # RSI-14
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss
    rsi_14 = float(round(100 - (100 / (1 + rs.iloc[-1])), 2))

    # MACD (12/26/9)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line   = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    macd_val = float(round(macd_line.iloc[-1], 4))
    macd_sig = float(round(signal_line.iloc[-1], 4))

    # SMAs
    if len(close) >= 50:
        sma_50  = float(round(close.rolling(50).mean().iloc[-1], 2))
    if len(close) >= 200:
        sma_200 = float(round(close.rolling(200).mean().iloc[-1], 2))

    return rsi_14, macd_val, macd_sig, sma_50, sma_200


def _to_jk(ticker: str) -> str:
    return f"{ticker.upper().replace('.JK', '')}.JK"


def fetch_market_data(ticker: str) -> MarketData:
    """
    Fetch market data for an IDX stock.
    - Price / OHLCV / Technicals: datasectors API (if SECRET_TOKEN set), else yfinance
    - Fundamentals (PE, PB, sector, etc.): yfinance
    """
    hist        = pd.DataFrame()
    price       = 0.0
    change_pct  = 0.0
    volume      = 0
    avg_vol_10d = 0
    high_52w    = low_52w = None
    ds_ok       = False

    # ── 1. datasectors for OHLCV ─────────────────────────────────
    if DATASECTORS_KEY and DATASECTORS_KEY not in ("", "nilai_key_disini"):
        try:
            hist = _fetch_datasectors_ohlcv(ticker, days=365)
            if not hist.empty and "Close" in hist.columns:
                c = hist["Close"].dropna()
                if len(c) >= 2:
                    price      = float(c.iloc[-1])
                    prev       = float(c.iloc[-2])
                    change_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
                    high_52w   = float(c.max())
                    low_52w    = float(c.min())
                    ds_ok      = True
                if "Volume" in hist.columns:
                    v           = hist["Volume"].dropna()
                    volume      = int(v.iloc[-1]) if len(v) else 0
                    avg_vol_10d = int(v.tail(10).mean()) if len(v) >= 10 else volume
            if ds_ok:
                print(f"  [datasectors] {ticker}: Rp{price:,.0f} {change_pct:+.2f}%")
        except Exception as e:
            print(f"  [datasectors] {ticker} error: {e} — fallback to yfinance")

    # ── 2. yfinance: fundamentals + fallback price if datasectors failed ──
    pe = pb = mktcap = rev_gr = roe = de = sector = None
    try:
        stock = yf.Ticker(_to_jk(ticker))
        info  = stock.info or {}

        pe     = info.get("trailingPE")
        pb     = info.get("priceToBook")
        mktcap = info.get("marketCap")
        rev_gr = info.get("revenueGrowth")
        roe    = info.get("returnOnEquity")
        de     = info.get("debtToEquity")
        sector = info.get("sector")

        if not ds_ok:
            price       = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0)
            change_pct  = float(info.get("regularMarketChangePercent", 0) or 0)
            volume      = int(info.get("regularMarketVolume", 0) or 0)
            avg_vol_10d = int(info.get("averageDailyVolume10Day", 0) or 0)
            high_52w    = info.get("fiftyTwoWeekHigh")
            low_52w     = info.get("fiftyTwoWeekLow")
            hist        = stock.history(period="1y")
    except Exception as e:
        print(f"  [yfinance] {ticker} error: {e}")

    # ── 3. Technicals ─────────────────────────────────────────────
    rsi_14, macd_val, macd_sig, sma_50, sma_200 = _calc_technicals(hist)

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
