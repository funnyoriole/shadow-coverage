import json, os, time
import urllib.request
import feedparser
import yfinance as yf
from datetime import datetime
import pytz

GEMINI_API_KEY = os.environ["GEMINI_API_KEY_MACRO"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)

# ── Market snapshot ────────────────────────────────────────────
MARKET_TICKERS = {
    "S&P 500":      "^GSPC",
    "Nasdaq":       "^IXIC",
    "Dow Jones":    "^DJI",
    "VIX":          "^VIX",
    "ASX 200":      "^AXJO",
    "Nikkei 225":   "^N225",
    "FTSE 100":     "^FTSE",
    "AUD/USD":      "AUDUSD=X",
    "US 10Y Yield": "^TNX",
    "Oil (WTI)":    "CL=F",
    "Gold":         "GC=F",
    "Iron Ore":     "TIO=F",
}

def get_market_snapshot() -> list[dict]:
    rows = []
    for name, ticker in MARKET_TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d", interval="1d")
            if len(hist) < 2:
                continue
            prev = float(hist["Close"].iloc[-2])
            curr = float(hist["Close"].iloc[-1])
            pct  = ((curr - prev) / prev) * 100
            rows.append({"name": name, "price": round(curr, 2), "pct": round(pct, 2)})
        except Exception:
            continue
    return rows

def format_snapshot(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        arrow = "▲" if r["pct"] >= 0 else "▼"
        lines.append(f"  {r['name']:<18} {r['price']:>10.2f}   {arrow} {abs(r['pct']):.1f}%")
    return "\n".join(lines)

# ── News feeds ─────────────────────────────────────────────────
NEWS_FEEDS = [
    # Global macro & markets
    ("Reuters Markets",      "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters World",        "https://feeds.reuters.com/Reuters/worldNews"),
    ("Bloomberg Markets",    "https://feeds.bloomberg.com/markets/news.rss"),
    ("FT Markets",           "https://www.ft.com/markets?format=rss"),
    # AU specific
    ("AFR",                  "https://www.afr.com/rss"),
    ("RBA News",             "https://www.rba.gov.au/rss/rss-cb-speeches.xml"),
    # US macro
    ("WSJ Economy",          "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
    # Geopolitics
    ("BBC World",            "https://feeds.bbci.co.uk/news/world/rss.xml"),
]

def fetch_news(max_per_feed: int = 6) -> list[dict]:
    all_items = []
    for source, url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:max_per_feed]:
                pub  = e.get("published_parsed")
                time_str = (
                    datetime(*pub[:6]).strftime("%d %b %H:%M")
                    if pub else "recent"
                )
                all_items.append({
                    "source": source,
                    "time":   time_str,
                    "title":  e.get("title", "").strip(),
                    "summary": e.get("summary", "")[:200].strip(),
                })
        except Exception:
            continue
    return all_items

def format_news(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(f"  [{item['time']}] [{item['source']}] {item['title']}")
        if item["summary"]:
            lines.append(f"    {item['summary']}")
    return "\n".join(lines)

# ── Gemini call (plain, no grounding) ─────────────────────────
def call_gemini(prompt: str, retries: int = 3, wait: int = 60) -> str:
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.2}
    }).encode()

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                GEMINI_URL,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
            parts = resp["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except Exception as e:
            if attempt == retries:
                raise
            print(f"  Attempt {attempt} failed ({e}) — retrying in {wait}s...")
            time.sleep(wait)

# ── Prompt ─────────────────────────────────────────────────────
def build_prompt(snapshot_text: str, news_text: str, date_str: str) -> str:
    return f"""You are a senior equity research analyst writing a morning intelligence brief for {date_str}.

Your reader covers Australian and US equities, specifically A-REITs and BNPL/fintech stocks.

Below is today's market data and a raw news feed from the last 12 hours.
Your job is to synthesise the most important developments — do not simply list headlines.

MARKET SNAPSHOT:
{snapshot_text}

NEWS FEED:
{news_text}

Write a morning brief using exactly these section headers:
## Overnight Markets
## Central Banks & Rates
## US Macro & Earnings
## Geopolitics & Global Risks
## China & Commodities
## Australia
## Sector Watch: A-REITs & Fintech

Rules:
- 2–4 sentences per section of tight analyst prose
- Start the 1–2 most important sentences across the whole brief with [KEY]
- Link market moves to news causes where the evidence supports it
- If nothing significant happened in a section, say so in one sentence
- Do not speculate beyond what the news feed contains
- Total length: ~400 words"""

# ── Main ───────────────────────────────────────────────────────
def generate_macro_brief() -> dict:
    sydney   = pytz.timezone("Australia/Sydney")
    date_str = datetime.now(sydney).strftime("%A, %d %B %Y")

    print("→ Fetching market snapshot...")
    snapshot      = get_market_snapshot()
    snapshot_text = format_snapshot(snapshot)

    print("→ Fetching news feeds...")
    news_items = fetch_news()
    news_text  = format_news(news_items)
    print(f"  {len(news_items)} headlines collected")

    print("→ Calling Gemini for macro brief...")
    try:
        brief = call_gemini(build_prompt(snapshot_text, news_text, date_str))
    except Exception as e:
        brief = f"Macro brief unavailable: {e}"

    result = {"date": date_str, "snapshot": snapshot, "brief": brief}

    with open("macro_report.json", "w") as f:
        json.dump(result, f, indent=2)
    print("✓ macro_report.json written")
    return result

if __name__ == "__main__":
    generate_macro_brief()
