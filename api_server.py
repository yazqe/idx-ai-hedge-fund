"""Local API server — real-time single-ticker analysis via browser."""
import json, threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_file, redirect
from flask_cors import CORS
import pytz

WIB  = pytz.timezone('Asia/Jakarta')
ROOT = Path(__file__).parent
app  = Flask(__name__, static_folder=str(ROOT / "analysis"), static_url_path="/static")
CORS(app)

_running: dict = {}   # ticker → "running" | "done" | "error"
_results: dict = {}   # ticker → result dict
_started: dict = {}   # ticker → timestamp when analysis started

ANALYSIS_TIMEOUT = 300  # 5 minutes max


def _do_analysis(ticker: str):
    import time
    from batch_analysis import run_analysis
    _running[ticker] = "running"
    _started[ticker] = time.time()
    try:
        result = run_analysis(ticker)
        if result:
            _results[ticker] = result
            _running[ticker] = "done"
        else:
            _running[ticker] = "error"
    except Exception as e:
        print(f"  ❌ Analysis error for {ticker}: {e}")
        _running[ticker] = "error"


@app.route("/api/analyze/<ticker>", methods=["POST"])
def analyze(ticker: str):
    import time
    ticker = ticker.upper()
    # Auto-reset if stuck beyond timeout
    if _running.get(ticker) == "running":
        elapsed = time.time() - _started.get(ticker, 0)
        if elapsed < ANALYSIS_TIMEOUT:
            return jsonify({"status": "running", "ticker": ticker})
        else:
            _running[ticker] = "error"  # force reset
    t = threading.Thread(target=_do_analysis, args=(ticker,), daemon=True)
    t.start()
    return jsonify({"status": "started", "ticker": ticker})


@app.route("/api/reset/<ticker>", methods=["POST"])
def reset(ticker: str):
    ticker = ticker.upper()
    _running.pop(ticker, None)
    _results.pop(ticker, None)
    _started.pop(ticker, None)
    return jsonify({"status": "reset", "ticker": ticker})


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


@app.route("/")
def index():
    """Serve dashboard locally — no mixed-content issues."""
    return send_file(ROOT / "analysis" / "index.html")

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/data/latest.json")
def latest_json():
    return send_file(ROOT / "analysis" / "data" / "latest.json")


if __name__ == "__main__":
    import os
    cert = Path(__file__).parent / "certs" / "cert.pem"
    key  = Path(__file__).parent / "certs" / "key.pem"
    ssl_ctx = (str(cert), str(key)) if cert.exists() and key.exists() else None
    proto = "https" if ssl_ctx else "http"
    print("🌐 IDX AI Hedge Fund Local API")
    print(f"   {proto}://127.0.0.1:8765/")
    print(f"   {proto}://127.0.0.1:8765/api/health\n")
    app.run(host="0.0.0.0", port=8765, debug=False, ssl_context=ssl_ctx)
