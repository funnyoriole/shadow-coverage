# ── Watchlist ──────────────────────────────────────────────────
# Add or remove stocks here. Everything else updates automatically.
WATCHLIST = [
    {"ticker": "ARF.AX", "name": "Arena REIT", "asx_code": "ARF"},
    {"ticker": "ZIP.AX", "name": "Zip Co",      "asx_code": "ZIP"},
    # {"ticker": "CBA.AX", "name": "Commonwealth Bank", "asx_code": "CBA"},
]

# ── Email subjects ─────────────────────────────────────────────
EMAIL_SUBJECT_STOCKS = "Shadow Coverage Daily Brief"
EMAIL_SUBJECT_MACRO  = "Morning Intelligence Brief"

# ── Causality engine thresholds ────────────────────────────────
BIG_MOVE_PCT  = 3.0   # use 24h event window
SMALL_MOVE_PCT = 1.0  # use 6h event window
ALERT_PCT     = 5.0   # reserved for future alert logic

# ── Event scoring weights ──────────────────────────────────────
EVENT_WEIGHTS = {
    "earnings":        10,
    "guidance":         9,
    "capital_raise":    8,
    "dividend":         7,
    "director_change":  6,
    "announcement":     4,
    "news":             3,
    "sector":           1,
}
