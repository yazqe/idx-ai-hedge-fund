"""Local/Cloud API server — real-time single-ticker analysis."""
import json, os, threading
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pytz
import progress_tracker as PT

WIB  = pytz.timezone('Asia/Jakarta')
ROOT = Path(__file__).parent
app  = Flask(__name__, static_folder=str(ROOT / "analysis"), static_url_path="/static")
CORS(app)

# ── PIN protection (set API_PIN env var to enable) ─────────────
API_PIN = os.environ.get("API_PIN", "").strip()

def _check_pin():
    if not API_PIN:
        return True
    return request.headers.get("X-API-Pin", "") == API_PIN

def _pin_error():
    return jsonify({"error": "PIN required", "code": 401}), 401

# ── Rate limiting (max analyses per IP per day) ─────────────────
import time as _time
from collections import defaultdict

DAILY_LIMIT   = int(os.environ.get("DAILY_LIMIT", "10"))  # per IP per day
_rate_log     = defaultdict(list)  # ip → [timestamps]

def _get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()

def _check_rate():
    """Return True if within rate limit."""
    if not DAILY_LIMIT:
        return True
    ip  = _get_ip()
    now = _time.time()
    day = 86400
    _rate_log[ip] = [t for t in _rate_log[ip] if now - t < day]
    if len(_rate_log[ip]) >= DAILY_LIMIT:
        return False
    _rate_log[ip].append(now)
    return True

def _rate_error():
    ip = _get_ip()
    used = len(_rate_log[ip])
    return jsonify({
        "error": f"Batas harian tercapai ({used}/{DAILY_LIMIT} analisis). Coba lagi besok.",
        "code": 429, "used": used, "limit": DAILY_LIMIT
    }), 429

# ── In-memory state ────────────────────────────────────────────
_running: dict = {}
_results: dict = {}
_started: dict = {}
ANALYSIS_TIMEOUT = 300


def _do_analysis(ticker: str):
    import time
    from batch_analysis import run_analysis
    _running[ticker] = "running"
    _started[ticker] = time.time()
    PT.update(ticker, "start")
    try:
        result = run_analysis(ticker)
        if result:
            _results[ticker] = result
            _running[ticker] = "done"
            PT.update(ticker, "done")
        else:
            _running[ticker] = "error"
    except Exception as e:
        print(f"  ❌ {ticker}: {e}")
        _running[ticker] = "error"


# ── Routes ─────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    ip   = _get_ip()
    now  = _time.time()
    used = len([t for t in _rate_log.get(ip, []) if now - t < 86400])
    has_pin = bool(API_PIN) and (request.headers.get("X-API-Pin","") == API_PIN)
    return jsonify({
        "ok": True,
        "time": datetime.now(WIB).strftime("%H:%M WIB"),
        "pin_required": False,          # no longer blocks access
        "unlimited": has_pin,           # True if valid PIN = no rate limit
        "rate": {"used": used, "limit": DAILY_LIMIT if not has_pin else 0},
    })

@app.route("/api/verify-pin", methods=["POST"])
def verify_pin():
    if not API_PIN:
        return jsonify({"valid": True, "pin_required": False})
    pin = request.json.get("pin", "") if request.is_json else ""
    return jsonify({"valid": pin == API_PIN, "pin_required": True})

@app.route("/api/analyze/<ticker>", methods=["POST"])
def analyze(ticker: str):
    import time
    # Valid PIN = unlimited access; no/wrong PIN = rate limited
    has_valid_pin = bool(API_PIN) and _check_pin()
    if not has_valid_pin:
        if not _check_rate():
            return _rate_error()
    ticker = ticker.upper()
    if _running.get(ticker) == "running":
        elapsed = time.time() - _started.get(ticker, 0)
        if elapsed < ANALYSIS_TIMEOUT:
            return jsonify({"status": "running", "ticker": ticker})
        _running[ticker] = "error"
    t = threading.Thread(target=_do_analysis, args=(ticker,), daemon=True)
    t.start()
    return jsonify({"status": "started", "ticker": ticker})

@app.route("/api/result/<ticker>")
def result(ticker: str):
    if not _check_pin():
        return _pin_error()
    ticker = ticker.upper()
    status = _running.get(ticker, "idle")
    progress = PT.get(ticker)
    if status == "done" and ticker in _results:
        return jsonify({"status": "done", "result": _results[ticker], "progress": progress})
    return jsonify({"status": status, "ticker": ticker, "progress": progress})

@app.route("/api/reset/<ticker>", methods=["POST"])
def reset(ticker: str):
    ticker = ticker.upper()
    _running.pop(ticker, None)
    _results.pop(ticker, None)
    _started.pop(ticker, None)
    return jsonify({"status": "reset", "ticker": ticker})

@app.route("/")
def index():
    return send_file(ROOT / "analysis" / "index.html")

@app.route("/data/latest.json")
def latest_json():
    return send_file(ROOT / "analysis" / "data" / "latest.json")

@app.route("/favicon.ico")
def favicon():
    return "", 204


if __name__ == "__main__":
    # Local: use HTTPS cert if available; Railway: plain HTTP (TLS handled by proxy)
    IS_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PORT"))
    port = int(os.environ.get("PORT", 8765))

    if IS_RAILWAY:
        ssl_ctx = None
        proto   = "http"
    else:
        cert = ROOT / "certs" / "cert.pem"
        key  = ROOT / "certs" / "key.pem"
        ssl_ctx = (str(cert), str(key)) if cert.exists() and key.exists() else None
        proto   = "https" if ssl_ctx else "http"

    pin_status = f"PIN: {'enabled ✅' if API_PIN else 'disabled (set API_PIN to enable)'}"
    print(f"🌐 IDX AI Hedge Fund API  |  {pin_status}")
    print(f"   {proto}://{'0.0.0.0' if IS_RAILWAY else '127.0.0.1'}:{port}/\n")
    app.run(host="0.0.0.0", port=port, debug=False, ssl_context=ssl_ctx)
