import yfinance as yf
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import pytz
import re

# ── Stock price data ───────────────────────────────────────────
def get_price_data(ticker: str) -> dict | None:
    t        = yf.Ticker(ticker)
    intraday = t.history(period="1d", interval="1m")
    daily    = t.history(period="3d", interval="1d")

    if len(daily) < 3:
        return None

    last_bar  = intraday.iloc[-1]
    curr      = float(last_bar["Close"])
    last_time = intraday.index[-1]

    sydney        = pytz.timezone("Australia/Sydney")
    timestamp_str = last_time.astimezone(sydney).strftime("%d %b %Y %I:%M %p AEST")

    prev       = float(daily["Close"].iloc[-2])
    day_before = float(daily["Close"].iloc[-3])
    pct        = ((curr - prev) / prev) * 100
    pct_yest   = ((prev - day_before) / day_before) * 100

    return {
        "price":           round(curr, 3),
        "timestamp":       timestamp_str,
        "prev_close":      round(prev, 3),
        "pct_change":      round(pct, 2),
        "pct_change_prev": round(pct_yest, 2),
        "day_high":        round(float(intraday["High"].max()), 3),
        "day_low":         round(float(intraday["Low"].min()),  3),
        "volume":          int(intraday["Volume"].sum()),
    }

# ── ASX announcements via MarketIndex RSS ─────────────────────
def get_announcements(asx_code: str) -> list[dict]:
    url  = f"https://www.marketindex.com.au/rss/announcements/{asx_code.lower()}"
    feed = feedparser.parse(url)
    out  = []
    for e in feed.entries[:8]:
        pub = e.get("published_parsed")
        ts  = datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.now(timezone.utc)
        out.append({
            "type":     classify_announcement(e.title),
            "time":     ts,
            "time_str": ts.strftime("%H:%M"),
            "title":    e.title.strip(),
            "link":     e.get("link", ""),
            "source":   "ASX",
        })
    return out

_PATTERNS = {
    "earnings":        r"(result|earnings|revenue|profit|loss|ebit|ebitda|npat)",
    "guidance":        r"(guidance|outlook|forecast|update|reaffirm)",
    "capital_raise":   r"(placement|raise|entitlement|capital|spp|rights issue)",
    "dividend":        r"(dividend|distribution|dps)",
    "director_change": r"(director|ceo|cfo|chair|appoint|resign|board)",
}

def classify_announcement(title: str) -> str:
    t = title.lower()
    for label, pattern in _PATTERNS.items():
        if re.search(pattern, t):
            return label
    return "announcement"

# ── News via Google News RSS ───────────────────────────────────
def get_news(company_name: str, asx_code: str) -> list[dict]:
    queries = [f"{company_name} ASX", f"{asx_code} ASX announcement"]
    seen, out = set(), []
    for q in queries:
        url  = f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=en-AU&gl=AU&ceid=AU:en"
        feed = feedparser.parse(url)
        for e in feed.entries[:5]:
            if e.title in seen:
                continue
            seen.add(e.title)
            pub = e.get("published_parsed")
            ts  = datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.now(timezone.utc)
            out.append({
                "type":     "news",
                "time":     ts,
                "time_str": ts.strftime("%H:%M"),
                "title":    e.title.strip(),
                "link":     e.get("link", ""),
                "source":   e.get("source", {}).get("title", "News"),
            })
    out.sort(key=lambda x: x["time"], reverse=True)
    return out[:6]

# ── ASX 200 sector move ────────────────────────────────────────
def get_sector_move(sector_ticker: str = "^AXJO") -> float | None:
    try:
        hist = yf.Ticker(sector_ticker).history(period="2d", interval="1d")
        if len(hist) < 2:
            return None
        prev = float(hist["Close"].iloc[-2])
        curr = float(hist["Close"].iloc[-1])
        return round(((curr - prev) / prev) * 100, 2)
    except Exception:
        return None
