import yfinance as yf
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re

# ── Prices ─────────────────────────────────────────────────────
def get_price_data(ticker: str) -> dict | None:
    t    = yf.Ticker(ticker)
    hist = t.history(period="2d", interval="1d")
    if len(hist) < 2:
        return None
    prev  = hist["Close"].iloc[-2]
    curr  = hist["Close"].iloc[-1]
    pct   = ((curr - prev) / prev) * 100
    info  = t.fast_info
    return {
        "price":      round(float(curr), 3),
        "prev_close": round(float(prev), 3),
        "pct_change": round(float(pct), 2),
        "day_high":   round(float(hist["High"].iloc[-1]), 3),
        "day_low":    round(float(hist["Low"].iloc[-1]),  3),
        "volume":     int(hist["Volume"].iloc[-1]),
        "market_cap": getattr(info, "market_cap", None),
    }

# ── ASX Announcements via MarketIndex RSS ──────────────────────
# MarketIndex provides clean per-stock RSS — far more reliable
# than scraping the ASX HTML table directly.
def get_announcements(asx_code: str) -> list[dict]:
    url  = f"https://www.marketindex.com.au/rss/announcements/{asx_code.lower()}"
    feed = feedparser.parse(url)
    out  = []
    for e in feed.entries[:8]:
        pub = e.get("published_parsed")
        ts  = datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.now(timezone.utc)
        out.append({
            "type":      classify_announcement(e.title),
            "time":      ts,
            "time_str":  ts.strftime("%H:%M"),
            "title":     e.title.strip(),
            "link":      e.get("link", ""),
            "source":    "ASX",
        })
    return out

# Classify announcement into a known event type for scoring
_PATTERNS = {
    "earnings":       r"(result|earnings|revenue|profit|loss|ebit|ebitda|npat)",
    "guidance":       r"(guidance|outlook|forecast|update|reaffirm)",
    "capital_raise":  r"(placement|raise|entitlement|capital|spp|rights issue)",
    "dividend":       r"(dividend|distribution|dps)",
    "director_change":r"(director|ceo|cfo|chair|appoint|resign|board)",
}
def classify_announcement(title: str) -> str:
    t = title.lower()
    for label, pattern in _PATTERNS.items():
        if re.search(pattern, t):
            return label
    return "announcement"

# ── News via Google News RSS ───────────────────────────────────
def get_news(company_name: str, asx_code: str) -> list[dict]:
    queries = [
        f"{company_name} ASX",
        f"{asx_code} ASX announcement",
    ]
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
    # sort newest first, cap at 6
    out.sort(key=lambda x: x["time"], reverse=True)
    return out[:6]

# ── Sector proxy (ASX 200 / REIT index as context) ────────────
def get_sector_move(sector_ticker: str = "^AXJO") -> float | None:
    try:
        t    = yf.Ticker(sector_ticker)
        hist = t.history(period="2d", interval="1d")
        if len(hist) < 2:
            return None
        prev = hist["Close"].iloc[-2]
        curr = hist["Close"].iloc[-1]
        return round(((curr - prev) / prev) * 100, 2)
    except Exception:
        return None
