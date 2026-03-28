import json, os

SENTIMENT_LABEL = {-2: "Very Negative", -1: "Cautious", 0: "Neutral", 1: "Positive", 2: "Strong Buy"}
SENTIMENT_COLOR = {-2: "#c62828", -1: "#ef6c00", 0: "#757575", 1: "#2e7d32", 2: "#1b5e20"}

def build():
    with open("report.json") as f:
        report = json.load(f)

    cards = ""
    for r in report["results"]:
        p   = r["price_data"]
        up  = p["pct_change"] >= 0
        clr = "#2e7d32" if up else "#c62828"
        bg  = "#f1f8e9" if up else "#ffebee"
        arrow = "▲" if up else "▼"
        s_clr = SENTIMENT_COLOR.get(r["sentiment"], "#757575")
        s_lbl = SENTIMENT_LABEL.get(r["sentiment"], "Neutral")

        ann_items = "".join(
            f"<li><span class='time'>{a['time']}</span> {a['title']}</li>"
            for a in r["announcements"]
        ) or "<li class='muted'>No announcements today</li>"

        news_items = "".join(
            f"<li><a href='{n['link']}' target='_blank'>{n['title']}</a>"
            f"<span class='source'> {n['source']}</span></li>"
            for n in r["news"]
        ) or "<li class='muted'>No news found</li>"

        cards += f"""
        <div class="card">
          <div class="card-header" style="background:{bg}">
            <div class="name-block">
              <h2>{r['stock']['name']}</h2>
              <span class="ticker">{r['stock']['ticker']}</span>
              <span class="sentiment" style="color:{s_clr}">● {s_lbl}</span>
            </div>
            <div class="price-block">
              <div class="price" style="color:{clr}">${p['price']}</div>
              <div class="change" style="color:{clr}">{arrow} {abs(p['pct_change'])}%</div>
              <div class="meta">Range: ${p['day_low']} – ${p['day_high']}</div>
              <div class="meta">Vol: {p['volume']:,}</div>
            </div>
          </div>
          <div class="summary">{r['summary']}</div>
          <div class="two-col">
            <div>
              <h4>ASX Announcements</h4>
              <ul class="ann-list">{ann_items}</ul>
            </div>
            <div>
              <h4>News</h4>
              <ul class="news-list">{news_items}</ul>
            </div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Shadow Coverage Brief</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
           max-width:860px;margin:0 auto;padding:24px;background:#f5f5f5;color:#222 }}
    h1   {{ font-size:22px;border-bottom:2px solid #222;padding-bottom:8px;margin-bottom:4px }}
    .sub {{ color:#666;font-size:13px;margin-bottom:24px }}
    .card {{ background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.1);
             margin-bottom:24px;overflow:hidden }}
    .card-header {{ display:flex;justify-content:space-between;align-items:flex-start;padding:18px 20px }}
    .name-block h2 {{ margin:0 0 4px;font-size:18px }}
    .ticker  {{ font-size:12px;color:#666;margin-right:10px }}
    .sentiment {{ font-size:12px;font-weight:600 }}
    .price-block {{ text-align:right }}
    .price  {{ font-size:28px;font-weight:700 }}
    .change {{ font-size:15px;font-weight:600 }}
    .meta   {{ font-size:12px;color:#666;margin-top:2px }}
    .summary {{ padding:14px 20px;font-size:14px;line-height:1.7;
                background:#fafafa;border-top:1px solid #eee;border-bottom:1px solid #eee }}
    .two-col {{ display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 20px }}
    h4 {{ margin:0 0 8px;font-size:13px;text-transform:uppercase;
          letter-spacing:.5px;color:#555 }}
    ul   {{ margin:0;padding-left:16px;font-size:13px;color:#333 }}
    li   {{ margin-bottom:5px;line-height:1.4 }}
    .time   {{ color:#888;font-size:11px;margin-right:4px }}
    .source {{ color:#999;font-size:11px }}
    .muted  {{ color:#aaa }}
    a {{ color:#1565c0;text-decoration:none }}
    a:hover {{ text-decoration:underline }}
    .footer {{ color:#bbb;font-size:11px;text-align:center;margin-top:32px }}
  </style>
</head>
<body>
  <h1>📊 Shadow Coverage Daily Brief</h1>
  <p class="sub">{report['date']} · Auto-generated at 11:00am AEST</p>
  {cards}
  <p class="footer">Automated summary — verify before acting on any information.</p>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w") as f:
        f.write(html)
    print("✓ Dashboard written to docs/index.html")

if __name__ == "__main__":
    build()
