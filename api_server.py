"""Local API server — real-time single-ticker analysis via browser."""
import json, threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import pytz

WIB = pytz.timezone('Asia/Jakarta')
app = Flask(__name__)
CORS(app)  # allow GitHub Pages → localhost calls

_running: dict = {}   # ticker → "running" | "done" | "error"
_results: dict = {}   # ticker → result dict


def _do_analysis(ticker: str):
    from batch_analysis import run_analysis
    _running[ticker] = "running"
    result = run_analysis(ticker)
    if result:
        _results[ticker] = result
        _running[ticker] = "done"
    else:
        _running[ticker] = "error"


@app.route("/api/analyze/<ticker>", methods=["POST"])
def analyze(ticker: str):
    ticker = ticker.upper()
    if _running.get(ticker) == "running":
        return jsonify({"status": "running", "ticker": ticker})
    t = threading.Thread(target=_do_analysis, args=(ticker,), daemon=True)
    t.start()
    return jsonify({"status": "started", "ticker": ticker})


@app.route("/api/result/<ticker>")
def result(ticker: str):
    ticker = ticker.upper()
    status = _running.get(ticker, "idle")
    if status == "done" and ticker in _results:
        return jsonify({"status": "done", "result": _results[ticker]})
    return jsonify({"status": status, "ticker": ticker})


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "time": datetime.now(WIB).strftime("%H:%M WIB")})


if __name__ == "__main__":
    print("🌐 IDX AI Hedge Fund Local API")
    print("   http://localhost:8765/api/health")
    print("   POST /api/analyze/<TICKER>")
    print("   GET  /api/result/<TICKER>\n")
    app.run(host="0.0.0.0", port=8765, debug=False)
