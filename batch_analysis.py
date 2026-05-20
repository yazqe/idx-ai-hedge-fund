"""Batch analysis — run AI Hedge Fund on top IDX candidates, save JSON results."""
import json, os, sys, time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pytz

WIB = pytz.timezone('Asia/Jakarta')
OUT_DIR = Path(__file__).parent / "analysis" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCANNER_URL = "https://scanner.tradingview.com/indonesia/scan"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://id.tradingview.com",
    "User-Agent": "Mozilla/5.0",
}
SUSPENDED = {"WBSA", "BAPA"}

# Saham NON-SYARIAH (bank konvensional, rokok, alkohol)
# Referensi: Daftar Efek Syariah OJK + Jakarta Islamic Index
NON_SYARIAH = {
    # Bank konvensional (mengandung riba)
    "BBCA", "BBRI", "BMRI", "BBNI", "BNGA", "BDMN", "NISP", "MEGA",
    "PNBN", "BJTM", "BNII", "BKSW", "AGRO", "BTPN", "BMAS", "BCIC",
    "BABP", "BBYB", "BGTG", "BINA", "BJBR", "BNBA",
    # Rokok / tembakau
    "HMSP", "GGRM", "WIIM", "ITIC",
    # Alkohol
    "MLBI", "DLTA",
}


def get_ihsg():
    """Fetch IHSG (Jakarta Composite Index) latest value."""
    try:
        r = requests.post(SCANNER_URL, headers=HEADERS, json={
            "symbols": {"tickers": ["IDX:COMPOSITE"]},
            "columns": ["close", "change", "change_abs"],
        }, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("data", [])
        if not data:
            return None
        d = data[0]["d"]
        return {"value": d[0], "change_pct": round(d[1], 2), "change_abs": round(d[2], 2)}
    except Exception:
        return None


def get_top_value_stocks(n=12):
    """Get top IDX stocks by trading value (most liquid — institutional focus)."""
    r = requests.post(SCANNER_URL, headers=HEADERS, json={
        "filter": [
            {"left": "Value.Traded", "operation": "greater", "right": 50_000_000_000},  # min Rp50B
            {"left": "volume",       "operation": "greater", "right": 5_000_000},
        ],
        "symbols": {"query": {"types": ["stock"]}},
        "columns": ["name", "close", "change", "volume", "Value.Traded"],
        "sort":    {"sortBy": "Value.Traded", "sortOrder": "desc"},
        "range":   [0, n + 5]
    }, timeout=15)
    if r.status_code != 200:
        return []
    result = []
    for item in r.json().get("data", []):
        code = item["d"][0].replace("IDX:", "")
        if code in SUSPENDED:
            continue
        result.append(code)
        if len(result) >= n:
            break
    return result


def get_top_gainers(n=5):
    """Get top IDX stocks by % price gain today."""
    r = requests.post(SCANNER_URL, headers=HEADERS, json={
        "filter": [
            {"left": "change", "operation": "greater", "right": 2},
            {"left": "volume", "operation": "greater", "right": 5_000_000},
        ],
        "symbols": {"query": {"types": ["stock"]}},
        "columns": ["name", "close", "change", "volume", "Value.Traded"],
        "sort":    {"sortBy": "change", "sortOrder": "desc"},
        "range":   [0, n + 5]
    }, timeout=15)
    if r.status_code != 200:
        return []
    result = []
    for item in r.json().get("data", []):
        code = item["d"][0].replace("IDX:", "")
        if code in SUSPENDED:
            continue
        result.append(code)
        if len(result) >= n:
            break
    return result


def get_top_frequency(n=5):
    """Get top IDX stocks by cross-list frequency (gainers + volume + value intersection)."""
    def scan(sort_by, filters=None):
        r = requests.post(SCANNER_URL, headers=HEADERS, json={
            "filter": filters or [],
            "symbols": {"query": {"types": ["stock"]}},
            "columns": ["name", "close", "change", "volume", "Value.Traded"],
            "sort": {"sortBy": sort_by, "sortOrder": "desc"},
            "range": [0, 30]
        }, timeout=15)
        if r.status_code != 200:
            return []
        return [item["d"][0].replace("IDX:", "")
                for item in r.json().get("data", [])
                if item["d"][0].replace("IDX:", "") not in SUSPENDED
                and (item["d"][3] or 0) > 10_000_000]

    gainers = scan("change", [
        {"left": "change", "operation": "greater", "right": 2},
        {"left": "volume", "operation": "greater", "right": 10_000_000},
    ])
    volume_stocks = scan("volume")
    value_stocks  = scan("Value.Traded")

    scores = {}
    for c in gainers:      scores[c] = scores.get(c, 0) + 2
    for c in volume_stocks: scores[c] = scores.get(c, 0) + 1
    for c in value_stocks:  scores[c] = scores.get(c, 0) + 1

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:n]]


def run_analysis(ticker: str):
    """Run full AI hedge fund analysis on a ticker, return dict or None on error."""
    try:
        from graph import build_graph
        graph = build_graph(None)  # no checkpoint for batch
        init = {
            "ticker": ticker.upper(),
            "market_data": None, "analyst_reports": [],
            "debate_result": None, "trade_proposal": None,
            "risk_review": None, "final_decision": None,
            "memory_context": "", "error": None,
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        }
        state = graph.invoke(init)

        if state.get("error"):
            print(f"  ⚠️  {ticker}: {state['error'][:80]}")
            return None

        fd = state.get("final_decision") or {}
        return {
            "ticker":           ticker,
            "decision":         fd.get("decision", "ERROR"),
            "action":           fd.get("action"),
            "entry_price":      fd.get("entry_price"),
            "target_price":     fd.get("target_price"),
            "stop_loss":        fd.get("stop_loss"),
            "position_size":    fd.get("position_size_pct", 0),
            "reasoning":        fd.get("reasoning", "")[:500],
            "analyst_signals":  [
                {"type": r["analyst_type"], "signal": r["signal"], "confidence": r["confidence"]}
                for r in state.get("analyst_reports", [])
            ],
            "debate_consensus": state.get("debate_result", {}).get("consensus"),
            "debate_winner":    state.get("debate_result", {}).get("winner"),
            "debate_summary":   (state.get("debate_result") or {}).get("summary", "")[:300],
            "risk_level":       (state.get("risk_review") or {}).get("risk_level"),
            "risk_approved":    (state.get("risk_review") or {}).get("approved"),
            "risk_flags":       (state.get("risk_review") or {}).get("risk_flags", []),
            "market_price":     (state.get("market_data") or {}).get("price"),
            "market_change":    (state.get("market_data") or {}).get("change_pct"),
            "sector":           (state.get("market_data") or {}).get("sector"),
            "rsi":              (state.get("market_data") or {}).get("rsi_14"),
            "analyzed_at":      datetime.now(WIB).strftime("%d %b %Y %H:%M WIB"),
        }
    except Exception as e:
        print(f"  ❌ {ticker} failed: {e}")
        return None


def main(tickers=None):
    now = datetime.now(WIB)
    print(f"\n🤖 IDX AI Hedge Fund — Batch Analysis")
    print(f"   {now.strftime('%d %B %Y %H:%M WIB')}\n")

    sources_map = {}  # ticker → list of source tags

    if not tickers:
        print("📊 Fetching top IDX stocks by trading VALUE (most liquid)...")
        value_list = get_top_value_stocks(10)
        print(f"   Top Value:     {', '.join(value_list)}")

        print("📈 Fetching top IDX gainers (% change today)...")
        gainer_list = get_top_gainers(5)
        print(f"   Top Gainers:   {', '.join(gainer_list) or 'none'}")

        print("🔄 Fetching top IDX by frequency (cross-list score)...")
        freq_list = get_top_frequency(5)
        print(f"   Top Frequency: {', '.join(freq_list) or 'none'}\n")

        for t in value_list:  sources_map.setdefault(t, []).append("VALUE")
        for t in gainer_list: sources_map.setdefault(t, []).append("GAINER")
        for t in freq_list:   sources_map.setdefault(t, []).append("FREQUENCY")
        tickers = list(sources_map.keys())
    else:
        for t in tickers:
            sources_map[t] = ["CUSTOM"]

    MAX_WORKERS = 3  # parallel stocks — keep low to avoid Anthropic rate limits
    results = []
    completed = 0

    def _analyze(ticker):
        srcs = sources_map.get(ticker, [])
        print(f"  → Starting {ticker} ({', '.join(srcs)})...")
        result = run_analysis(ticker)
        if result:
            result["sources"]    = srcs
            result["is_syariah"] = ticker not in NON_SYARIAH
        return ticker, result

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_analyze, t): t for t in tickers}
        for future in as_completed(futures):
            completed += 1
            ticker, result = future.result()
            if result:
                results.append(result)
                icon = {"EXECUTE": "✅", "MONITOR": "👀", "PASS": "⛔"}.get(result["decision"], "❓")
                print(f"  [{completed}/{len(tickers)}] {icon} {ticker}: {result['decision']} — {result['debate_consensus']} | Risk: {result['risk_level']}")
            else:
                print(f"  [{completed}/{len(tickers)}] ❌ {ticker}: failed")

    # Sort: EXECUTE first, then MONITOR, then PASS
    order = {"EXECUTE": 0, "MONITOR": 1, "PASS": 2, "ERROR": 3}
    results.sort(key=lambda x: (order.get(x["decision"], 3), x.get("position_size", 0) * -1))

    print("📈 Fetching IHSG...")
    ihsg = get_ihsg()
    if ihsg:
        print(f"   IHSG: {ihsg['value']:,.2f} ({ihsg['change_pct']:+.2f}%)")

    output = {
        "generated_at":    now.strftime("%d %B %Y %H:%M WIB"),
        "date":            now.strftime("%d %B %Y"),
        "ihsg":            ihsg,
        "total":           len(results),
        "execute_count":   sum(1 for r in results if r["decision"] == "EXECUTE"),
        "monitor_count":   sum(1 for r in results if r["decision"] == "MONITOR"),
        "pass_count":      sum(1 for r in results if r["decision"] == "PASS"),
        "value_count":     sum(1 for r in results if "VALUE"     in r.get("sources", [])),
        "gainer_count":    sum(1 for r in results if "GAINER"    in r.get("sources", [])),
        "frequency_count": sum(1 for r in results if "FREQUENCY" in r.get("sources", [])),
        "results":         results,
    }

    out_file = OUT_DIR / "latest.json"
    # Guard: never overwrite previous good data with an empty result set
    # (avoids early-morning runs wiping the display when filters return nothing)
    if not results and out_file.exists():
        try:
            existing = json.loads(out_file.read_text())
            if existing.get("results"):
                print(f"\n⚠️  Skip overwrite: 0 results — preserving previous "
                      f"({existing.get('total', 0)} stocks, {existing.get('generated_at','?')})")
                return existing
        except Exception:
            pass

    with open(out_file, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done — {len(results)} stocks analyzed")
    print(f"   EXECUTE: {output['execute_count']} | MONITOR: {output['monitor_count']} | PASS: {output['pass_count']}")
    print(f"   Saved: {out_file}")
    return output


if __name__ == "__main__":
    custom = sys.argv[1:] if len(sys.argv) > 1 else None
    main(custom)
