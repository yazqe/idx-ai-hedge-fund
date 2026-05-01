"""Batch analysis — run AI Hedge Fund on top IDX candidates, save JSON results."""
import json, os, sys, time
from datetime import datetime
from pathlib import Path
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


def get_top_candidates(n=15):
    """Get top IDX stocks by combining gainers + volume + value intersection."""
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
        return [(item["d"][0].replace("IDX:", ""), item["d"][2], item["d"][3])
                for item in r.json().get("data", [])
                if item["d"][0].replace("IDX:", "") not in SUSPENDED
                and (item["d"][3] or 0) > 10_000_000]  # min 10M volume

    gainers = {c: chg for c, chg, _ in scan("change", [
        {"left": "change", "operation": "greater", "right": 3},
        {"left": "volume", "operation": "greater", "right": 10_000_000},
    ])}
    volume_stocks = {c for c, _, _ in scan("volume")}
    value_stocks  = {c for c, _, _ in scan("Value.Traded")}

    # Score: triple=3, double=2, single=1
    scores = {}
    for c, chg in gainers.items():
        scores[c] = scores.get(c, 0) + 1 + (chg / 100)  # weight by gain %
    for c in volume_stocks:
        scores[c] = scores.get(c, 0) + 1
    for c in value_stocks:
        scores[c] = scores.get(c, 0) + 1

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

    if not tickers:
        print("📊 Fetching top IDX candidates...")
        tickers = get_top_candidates(12)
        print(f"   Candidates: {', '.join(tickers)}\n")

    results = []
    for i, ticker in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] Analyzing {ticker}...")
        result = run_analysis(ticker)
        if result:
            results.append(result)
            icon = {"EXECUTE": "✅", "MONITOR": "👀", "PASS": "⛔"}.get(result["decision"], "❓")
            print(f"  {icon} {result['decision']} — {result['debate_consensus']} | Risk: {result['risk_level']}")
        time.sleep(2)  # Rate limit

    # Sort: EXECUTE first, then MONITOR, then PASS
    order = {"EXECUTE": 0, "MONITOR": 1, "PASS": 2, "ERROR": 3}
    results.sort(key=lambda x: (order.get(x["decision"], 3), x.get("position_size", 0) * -1))

    output = {
        "generated_at": now.strftime("%d %B %Y %H:%M WIB"),
        "date":         now.strftime("%d %B %Y"),
        "total":        len(results),
        "execute_count": sum(1 for r in results if r["decision"] == "EXECUTE"),
        "monitor_count": sum(1 for r in results if r["decision"] == "MONITOR"),
        "pass_count":    sum(1 for r in results if r["decision"] == "PASS"),
        "results":      results,
    }

    out_file = OUT_DIR / "latest.json"
    with open(out_file, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done — {len(results)} stocks analyzed")
    print(f"   EXECUTE: {output['execute_count']} | MONITOR: {output['monitor_count']} | PASS: {output['pass_count']}")
    print(f"   Saved: {out_file}")
    return output


if __name__ == "__main__":
    custom = sys.argv[1:] if len(sys.argv) > 1 else None
    main(custom)
