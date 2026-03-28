import json, os, re
from datetime import date
import urllib.request
from config import WATCHLIST
from data_ingestion import get_price_data, get_announcements, get_news, get_sector_move
from causality_engine import build_llm_context

GEMINI_API_KEY = os.environ["AIzaSyBYdpC9niTnAmKQrDXzMXTdU0Em28G0Dto"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY
)

# ── LLM call via Gemini (no extra libraries needed) ───────────
def call_gemini(prompt: str) -> str:
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 400, "temperature": 0.2}
    }).encode()
    req = urllib.request.Request(
        GEMINI_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    return resp["candidates"][0]["content"]["parts"][0]["text"].strip()

# ── Prompt: structured evidence in, causal reasoning out ──────
def build_prompt(ctx: dict) -> str:
    p         = ctx["price_data"]
    name      = ctx["stock"]["name"]
    tkr       = ctx["stock"]["ticker"]
    move      = p["pct_change"]
    direction = "up" if move >= 0 else "down"

    if ctx["top_events"]:
        evidence = "\n".join(
            f"  [{e['time_str']} AEST] [{e['type'].upper()}] {e['title']}"
            for e in ctx["top_events"]
        )
    else:
        evidence = "  No material events found in the relevant time window."

    sector_line = (
        f"ASX 200 today: {ctx['sector_move']:+.1f}%"
        if ctx["sector_move"] is not None else "ASX 200: unavailable"
    )

    return f"""You are a buy-side equity analyst providing a daily shadow coverage brief.

Stock: {name} ({tkr})
Price: ${p['price']} ({direction} {abs(move):.1f}% from yesterday's close of ${p['prev_close']})
Day range: ${p['day_low']} – ${p['day_high']} | Volume: {p['volume']:,}
{sector_line}

Evidence (time-ordered, pre-filtered, scored by relevance):
{evidence}

Instructions:
1. Identify the most likely driver(s) of today's price move using only the evidence above.
2. Explain the causality clearly — how does the event explain the magnitude of the move?
3. If no clear catalyst exists, say: "No clear catalyst identified — move likely reflects [sector/market/noise]."
4. Note any follow-up items the analyst should monitor.
5. Write 3–4 sentences in professional analyst prose. No bullet points. No speculation beyond the evidence.

Do not invent information not present in the evidence list."""

# ── Main orchestration ─────────────────────────────────────────
def build_report() -> dict:
    today     = date.today().strftime("%A, %d %B %Y")
    sector_mv = get_sector_move()
    results   = []

    for stock in WATCHLIST:
        print(f"→ Processing {stock['name']}...")
        price_data = get_price_data(stock["ticker"])
        if not price_data:
            print(f"  ✗ No price data for {stock['ticker']} — skipping")
            continue

        announcements = get_announcements(stock["asx_code"])
        news          = get_news(stock["name"], stock["asx_code"])
        all_events    = announcements + news
        ctx           = build_llm_context(stock, price_data, all_events, sector_mv)

        try:
            summary = call_gemini(build_prompt(ctx))
        except Exception as e:
            summary = f"AI summarisation unavailable: {e}"

        results.append({
            "stock":      stock,
            "price_data": price_data,
            "summary":    summary,
            "confidence": ctx["confidence"],
            "top_events": [
                {**e, "time": e["time"].isoformat()} for e in ctx["top_events"]
            ],
            "all_events": [
                {**e, "time": e["time"].isoformat()} for e in ctx["all_events"]
            ],
        })

    report = {"date": today, "sector_move": sector_mv, "results": results}
    with open("report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("✓ report.json written")
    return report

if __name__ == "__main__":
    build_report()
