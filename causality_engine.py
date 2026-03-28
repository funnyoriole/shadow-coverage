from datetime import datetime, timedelta, timezone
from config import EVENT_WEIGHTS, BIG_MOVE_PCT, SMALL_MOVE_PCT

# ── Step 1: Build unified event timeline ──────────────────────
def build_event_timeline(announcements: list, news: list) -> list:
    """
    Merge announcements + news into a single time-sorted list.
    Each event: {type, time, time_str, title, link, source, score}
    """
    events = announcements + news
    events.sort(key=lambda e: e["time"])
    return events

# ── Step 2: Filter to relevant time window ────────────────────
def filter_relevant_events(events: list, pct_change: float) -> list:
    """
    Big moves (>3%) → look back 24h (could be pre-market news).
    Small moves (1-3%) → look back 6h.
    Tiny moves (<1%) → look back 2h (likely noise anyway).
    """
    now = datetime.now(timezone.utc)
    abs_move = abs(pct_change)

    if abs_move >= BIG_MOVE_PCT:
        window = timedelta(hours=24)
    elif abs_move >= SMALL_MOVE_PCT:
        window = timedelta(hours=6)
    else:
        window = timedelta(hours=2)

    cutoff = now - window
    return [e for e in events if e["time"] >= cutoff]

# ── Step 3: Score and rank events ─────────────────────────────
def score_events(events: list) -> list:
    """
    Score each event by:
    - Event type weight (earnings > news)
    - Recency bonus (more recent = higher score)
    Returns events sorted by score descending.
    """
    now = datetime.now(timezone.utc)
    scored = []
    for e in events:
        base   = EVENT_WEIGHTS.get(e["type"], 2)
        age_h  = (now - e["time"]).total_seconds() / 3600
        # recency: events < 1h ago get full bonus, decays over 24h
        recency = max(0, 1 - (age_h / 24))
        score   = base + (recency * 3)
        scored.append({**e, "score": round(score, 2)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

# ── Step 4: Assess confidence ─────────────────────────────────
def assess_confidence(pct_change: float, top_events: list) -> str:
    """
    Confidence is a function of:
    - Whether a high-weight event exists (earnings, guidance, raise)
    - Whether the move is large (easier to attribute)
    - Whether events are recent (time-proximate to move)

    Returns: "High" / "Medium" / "Low"
    """
    if not top_events:
        return "Low"

    top_score  = top_events[0]["score"] if top_events else 0
    top_type   = top_events[0]["type"]  if top_events else ""
    abs_move   = abs(pct_change)

    high_weight_types = {"earnings", "guidance", "capital_raise"}

    if top_type in high_weight_types and abs_move >= BIG_MOVE_PCT:
        return "High"
    elif top_score >= 6 and abs_move >= SMALL_MOVE_PCT:
        return "Medium"
    else:
        return "Low"

# ── Step 5: Assemble structured context for LLM ───────────────
def build_llm_context(stock: dict, price_data: dict,
                       all_events: list, sector_move: float | None) -> dict:
    """
    Returns a structured dict that the LLM prompt builder consumes.
    The LLM receives ONLY pre-filtered, scored evidence — never raw data.
    This is what prevents hallucination.
    """
    timeline  = build_event_timeline(
        [e for e in all_events if e["source"] == "ASX"],
        [e for e in all_events if e["source"] != "ASX"]
    )
    relevant  = filter_relevant_events(timeline, price_data["pct_change"])
    scored    = score_events(relevant)
    top_events = scored[:5]  # top 5 only — keep prompt tight
    confidence = assess_confidence(price_data["pct_change"], top_events)

    return {
        "stock":       stock,
        "price_data":  price_data,
        "top_events":  top_events,
        "all_events":  timeline,   # for display in dashboard
        "confidence":  confidence,
        "sector_move": sector_move,
    }
