"""Shared in-memory progress tracker for analysis pipeline."""
_progress = {}  # ticker → {"pct": int, "step": str}

STEPS = {
    "start":      (5,  "Memulai analisis..."),
    "fetch_data": (15, "Mengambil data pasar & harga..."),
    "memory":     (22, "Memuat histori analisis..."),
    "analysts":   (30, "Menjalankan 4 analis secara paralel..."),
    "analysts_done": (55, "Laporan analis selesai"),
    "debate":     (60, "Debat Bull vs Bear..."),
    "debate_done":(72, "Debat selesai"),
    "trader":     (75, "Trader membuat proposal..."),
    "trader_done":(82, "Proposal trading dibuat"),
    "risk":       (85, "Evaluasi risiko..."),
    "risk_done":  (90, "Risiko dievaluasi"),
    "pm":         (93, "Portfolio Manager memutuskan..."),
    "done":       (100,"Analisis selesai ✓"),
}

def update(ticker: str, step_key: str):
    pct, label = STEPS.get(step_key, (0, step_key))
    _progress[ticker.upper()] = {"pct": pct, "step": label}

def get(ticker: str) -> dict:
    return _progress.get(ticker.upper(), {"pct": 0, "step": "Menunggu..."})

def clear(ticker: str):
    _progress.pop(ticker.upper(), None)
