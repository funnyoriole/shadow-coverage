import json, os, time
from datetime import date
import urllib.request
from config import WATCHLIST
from data_ingestion import get_price_data, get_announcements, get_news, get_sector_move
from causality_engine import build_llm_context

GEMINI_API_KEY = os.environ["GEMINI_API_KEY_STOCKS"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)

def call_gemini(prompt: str, retries: int = 3, wait: int = 60) -> str:
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1200, "temperature": 0.2}
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

def build_batch_prompt(contexts: list) -> str:
    stocks_block = ""
    for i, ctx in enumerate(contexts):
        p         = ctx["price_data"]
        name      = ctx["stock"]["name"]
        tkr       = ctx["stock"]["ticker"]
        move      = p["pct_change"]
        prev_move = p.get("pct_change_prev", 0)
        direction = "up" if move >= 0 else "down"
        prev_dir  = "up" if prev_move >= 0 else "down"
        sector_line = (
            f"ASX 200 today: {ctx['sector_move']:+.1f}%"
            if ctx["sector_move"] is not None else "ASX 200: unavailable"
        )
        evidence = (
            "\n".join(
                f"    [{e['time_str']} AEST] [{e['type'].upper()}] {e['title']}"
                for e in ctx["top_events"]
            ) or "    No material events found in the relevant time window."
        )
        stocks_block += f"""
--- Stock {i+1}: {name} ({tkr}) ---
Today:     ${p['price']} ({direction} {abs(move):.1f}% from prev close ${p['prev_close']})
Yesterday: {prev_dir} {abs(prev_move):.1f}%
Day range: ${p['day_low']} – ${p['day_high']} | Volume: {p['volume']:,}
{sector_line}
Evidence:
{evidence}
"""
    return f"""You are a buy-side equity analyst providing daily shadow coverage briefs.

Below are {len(contexts)} ASX stocks. For each one:
1. Identify the most likely driver of today's price move using only the evidence provided.
2. Explain the causality clearly — how does the event explain the magnitude of the move?
3. Note whether today's move is a continuation or reversal of yesterday's direction.
4. If no clear catalyst exists, say: "No clear catalyst identified — move likely reflects [sector/market/noise]."
5. Note any follow-up items the analyst should monitor.
6. Write 3–4 sentences of professional analyst prose. No bullet points.

Return a JSON array, one object per stock, same order as input.
Each object must have exactly two keys: "ticker" and "summary".
Return only the JSON array, no other text.

Example:
[
  {{"ticker": "ARF.AX", "summary": "Arena REIT declined..."}},
  {{"ticker": "ZIP.AX", "summary": "Zip Co fell sharply..."}}
]

{stocks_block}"""

def parse_batch_response(raw: str, contexts: list) -> dict:
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        items = json.loads(clean)
        return {item["ticker"]: item["summary"] for item in items}
    except Exception:
        fallback = f"AI summarisation parse error. Raw: {raw[:200]}"
        return {ctx["stock"]["ticker"]: fallback for ctx in contexts}

def build_report() -> dict:
    today     = date.today().strftime("%A, %d %B %Y")
    sector_mv = get_sector_move()
    contexts  = []

    for stock in WATCHLIST:
        print(f"→ Fetching data for {stock['name']}...")
        price_data = get_price_data(stock["ticker"])
        if not price_data:
            print(f"  ✗ No price data for {stock['ticker']} — skipping")
            continue
        announcements = get_announcements(stock["asx_code"])
        news          = get_news(stock["name"], stock["asx_code"])
        ctx           = build_llm_context(stock, price_data, announcements + news, sector_mv)
        contexts.append(ctx)

    summaries = {}
    if contexts:
        print(f"→ Calling Gemini for {len(contexts)} stocks...")
        try:
            raw       = call_gemini(build_batch_prompt(contexts))
            summaries = parse_batch_response(raw, contexts)
        except Exception as e:
            print(f"  ✗ Gemini error: {e}")
            summaries = {ctx["stock"]["ticker"]: f"AI summarisation unavailable: {e}"
                         for ctx in contexts}

    results = []
    for ctx in contexts:
        tkr = ctx["stock"]["ticker"]
        results.append({
            "stock":      ctx["stock"],
            "price_data": ctx["price_data"],
            "summary":    summaries.get(tkr, "Summary unavailable."),
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
