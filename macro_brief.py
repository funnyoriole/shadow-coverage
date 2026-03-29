import json, os
import urllib.request
import yfinance as yf
from datetime import datetime
import pytz

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
# Use gemini-2.0-flash with Google Search grounding — pulls live news automatically
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)

# ── Market snapshot (overnight closes) ────────────────────────
MARKET_TICKERS = {
    "S&P 500":      "^GSPC",
    "Nasdaq":       "^IXIC",
    "Dow Jones":    "^DJI",
    "VIX":          "^VIX",
    "ASX 200":      "^AXJO",
    "Nikkei 225":   "^N225",
    "FTSE 100":     "^FTSE",
    "AUD/USD":      "AUDUSD=X",
    "USD/CNY":      "USDCNY=X",
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
            prev  = float(hist["Close"].iloc[-2])
            curr  = float(hist["Close"].iloc[-1])
            pct   = ((curr - prev) / prev) * 100
            rows.append({
                "name":   name,
                "price":  round(curr, 2),
                "pct":    round(pct, 2),
            })
        except Exception:
            continue
    return rows

def format_snapshot(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        arrow = "▲" if r["pct"] >= 0 else "▼"
        lines.append(f"  {r['name']:<18} {r['price']:>10.2f}   {arrow} {abs(r['pct']):.1f}%")
    return "\n".join(lines)

# ── Gemini call with Google Search grounding ──────────────────
def call_gemini_with_search(prompt: str) -> str:
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],   # enables live web search
        "generationConfig": {
            "maxOutputTokens": 1000,
            "temperature": 0.2
        }
    }).encode()
    req = urllib.request.Request(
        GEMINI_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())

    # Extract text from all parts (search grounding may split into multiple)
    parts = resp["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()

# ── Prompt ─────────────────────────────────────────────────────
def build_macro_prompt(snapshot_text: str, date_str: str) -> str:
    return f"""You are a senior equity research analyst writing a morning intelligence brief for {date_str}.

Your reader is an equity research analyst focused on Australian and US equities, 
with specific coverage of A-REITs and BNPL/fintech stocks.

Using your web search capability, find and summarise the most important developments 
from the last 24 hours across these areas:

1. OVERNIGHT MARKETS (use the data below — do not search for these)
{snapshot_text}

2. CENTRAL BANKS & RATES
   Search for: any Fed, RBA, ECB, PBOC rate decisions, meeting minutes, or 
   commentary in the last 24 hours. What is the current rate trajectory signal?

3. US MACRO & EARNINGS
   Search for: major US economic data releases (CPI, PPI, jobs, GDP, PMI), 
   and any significant S&P 500 earnings results overnight.

4. GEOPOLITICS & GLOBAL RISKS
   Search for: any geopolitical developments that could move markets — 
   trade policy (especially US-China), energy supply, Middle East, 
   major elections, sanctions, or policy shifts.

5. CHINA & COMMODITIES
   Search for: China economic data, property sector, iron ore demand signals, 
   oil supply/demand news. Relevant to AU equities.

6. AUSTRALIA SPECIFIC
   Search for: RBA commentary, AU economic data, ASX sector moves, 
   any AU government policy affecting markets.

7. SECTOR WATCH
   Search for: A-REIT sector news (interest rate sensitivity, cap rates, 
   property market), and BNPL/fintech news (regulation, consumer spending trends).

Format your response as a clean briefing with these exact section headers:
## Overnight Markets
## Central Banks & Rates
## US Macro & Earnings
## Geopolitics & Global Risks  
## China & Commodities
## Australia
## Sector Watch: A-REITs & Fintech

Under each header write 2–4 sentences of tight analyst prose. 
Flag the 1–2 most important items for today with [KEY] at the start of the sentence.
If nothing significant happened in a section, write one sentence saying so.
Total length: ~400 words."""

# ── Main ───────────────────────────────────────────────────────
def generate_macro_brief() -> dict:
    sydney   = pytz.timezone("Australia/Sydney")
    now_syd  = datetime.now(sydney)
    date_str = now_syd.strftime("%A, %d %B %Y")

    print("→ Fetching market snapshot...")
    snapshot      = get_market_snapshot()
    snapshot_text = format_snapshot(snapshot)

    print("→ Calling Gemini for macro brief (with web search)...")
    try:
        brief = call_gemini_with_search(
            build_macro_prompt(snapshot_text, date_str)
        )
    except Exception as e:
        brief = f"Macro brief unavailable: {e}"

    result = {
        "date":     date_str,
        "snapshot": snapshot,
        "brief":    brief,
    }

    with open("macro_report.json", "w") as f:
        json.dump(result, f, indent=2)
    print("✓ macro_report.json written")
    return result

if __name__ == "__main__":
    generate_macro_brief()
