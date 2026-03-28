import json, os

CONF_COLOR = {"High": "#2e7d32", "Medium": "#e65100", "Low": "#757575"}
CONF_BG    = {"High": "#e8f5e9", "Medium": "#fff3e0", "Low": "#f5f5f5"}

def build():
    with open("report.json") as f:
        report = json.load(f)

    sector_mv = report.get("sector_move")
    sector_html = ""
    if sector_mv is not None:
        clr = "#2e7d32" if sector_mv >= 0 else "#c62828"
        sector_html = f"&nbsp;·&nbsp; ASX 200: <b style='color:{clr}'>{sector_mv:+.1f}%</b>"

    cards = ""
    for r in report["results"]:
        p    = r["price_data"]
        up   = p["pct_change"] >= 0
        clr  = "#2e7d32" if up else "#c62828"
        bg   = "#f1f8e9" if up else "#ffebee"
        conf = r["confidence"]

        ev_rows = "".join(
            f"<tr>"
            f"<td style='color:#888;font-size:11px;white-space:nowrap;padding:3px 10px 3px 0'>{e['time_str']}</td>"
            f"<td style='padding:3px 10px 3px 0'><span style='background:#eee;border-radius:3px;"
            f"padding:1px 5px;font-size:10px;text-transform:uppercase'>{e['type']}</span></td>"
            f"<td style='font-size:12px;color:#333'>{e['title']}</td>"
            f"</tr>"
            for e in r["top_events"]
        ) or "<tr><td colspan='3' style='color:#aaa;font-size:12px;padding:4px 0'>No material events in window</td></tr>"

        cards += f"""
        <div style="background:#fff;border:1px solid #e0e0e0;border-radius:10px;
                    overflow:hidden;margin-bottom:24px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      padding:18px 20px;background:{bg}">
            <div>
              <div style="font-size:18px;font-weight:700;margin-bottom:4px">
                {r['stock']['name']}
                <span style="font-size:12px;color:#666;font-weight:400;margin-left:6px">
                  {r['stock']['ticker']}
                </span>
              </div>
              <span style="display:inline-block;background:{CONF_BG[conf]};
                           color:{CONF_COLOR[conf]};border-radius:4px;
                           padding:2px 8px;font-size:11px;font-weight:700">
                Confidence: {conf}
              </span>
            </div>
            <div style="text-align:right">
              <div style="font-size:26px;font-weight:700;color:{clr}">${p['price']}</div>
              <div style="font-size:14px;font-weight:600;color:{clr}">
                {'▲' if up else '▼'} {abs(p['pct_change']):.1f}%
              </div>
              <div style="font-size:11px;color:#888">
                Range: ${p['day_low']} – ${p['day_high']}
              </div>
              <div style="font-size:11px;color:#888">Vol: {p['volume']:,}</div>
            </div>
          </div>

          <div style="padding:14px 20px;font-size:14px;line-height:1.7;
                      background:#fafafa;border-top:1px solid #eee;border-bottom:1px solid #eee">
            {r['summary']}
          </div>

          <div style="padding:14px 20px">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                        color:#999;letter-spacing:.5px;margin-bottom:8px">
              Evidence used
            </div>
            <table style="width:100%;border-collapse:collapse">{ev_rows}</table>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Shadow Coverage Brief</title>
  <style>
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;
           max-width:740px;margin:0 auto;padding:24px;background:#f5f5f5;color:#222 }}
    h1   {{ font-size:20px;margin:0 0 4px }}
    .sub {{ color:#888;font-size:12px;margin:0 0 24px }}
    a    {{ color:#1565c0;text-decoration:none }}
    a:hover {{ text-decoration:underline }}
    .footer {{ color:#ccc;font-size:10px;text-align:center;margin-top:24px }}
  </style>
</head>
<body>
  <h1>📊 Shadow Coverage Daily Brief</h1>
  <p class="sub">{report['date']} · 11:00am AEST{sector_html}</p>
  {cards}
  <p class="footer">Auto-generated — verify before acting on any information.</p>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w") as f:
        f.write(html)
    print("✓ docs/index.html written")

if __name__ == "__main__":
    build()
