from datetime import datetime, timedelta, timezone
from config import EVENT_WEIGHTS, BIG_MOVE_PCT, SMALL_MOVE_PCT

def build_event_timeline(announcements: list, news: list) -> list:
    events = announcements + news
    events.sort(key=lambda e: e["time"])
    return events

def filter_relevant_events(events: list, pct_change: float) -> list:
    now      = datetime.now(timezone.utc)
    abs_move = abs(pct_change)
    if abs_move >= BIG_MOVE_PCT:
        window = timedelta(hours=24)
    elif abs_move >= SMALL_MOVE_PCT:
        window = timedelta(hours=6)
    else:
        window = timedelta(hours=2)
    cutoff = now - window
    return [e for e in events if e["time"] >= cutoff]

def score_events(events: list) -> list:
    now    = datetime.now(timezone.utc)
    scored = []
    for e in events:
        base    = EVENT_WEIGHTS.get(e["type"], 2)
        age_h   = (now - e["time"]).total_seconds() / 3600
        recency = max(0, 1 - (age_h / 24))
        score   = base + (recency * 3)
        scored.append({**e, "score": round(score, 2)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

def assess_confidence(pct_change: float, top_events: list) -> str:
    if not top_events:
        return "Low"
    top_score = top_events[0]["score"]
    top_type  = top_events[0]["type"]
    abs_move  = abs(pct_change)
    high_weight = {"earnings", "guidance", "capital_raise"}
    if top_type in high_weight and abs_move >= BIG_MOVE_PCT:
        return "High"
    elif top_score >= 6 and abs_move >= SMALL_MOVE_PCT:
        return "Medium"
    return "Low"

def build_llm_context(stock: dict, price_data: dict,
                      all_events: list, sector_move: float | None) -> dict:
    anns      = [e for e in all_events if e["source"] == "ASX"]
    news      = [e for e in all_events if e["source"] != "ASX"]
    timeline  = build_event_timeline(anns, news)
    relevant  = filter_relevant_events(timeline, price_data["pct_change"])
    scored    = score_events(relevant)
    top_events = scored[:5]
    confidence = assess_confidence(price_data["pct_change"], top_events)
    return {
        "stock":       stock,
        "price_data":  price_data,
        "top_events":  top_events,
        "all_events":  timeline,
        "confidence":  confidence,
        "sector_move": sector_move,
    }
