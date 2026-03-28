import json, os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import EMAIL_SENDER, EMAIL_RECIPIENT, EMAIL_SUBJECT

CONF_COLOR = {"High": "#2e7d32", "Medium": "#e65100", "Low": "#757575"}
CONF_BG    = {"High": "#e8f5e9", "Medium": "#fff3e0", "Low": "#f5f5f5"}

def build_html(report: dict) -> str:
    sector_line = (
        f"ASX 200: <b style='color:{'#2e7d32' if report['sector_move'] >= 0 else '#c62828'}'>"
        f"{report['sector_move']:+.1f}%</b>"
        if report.get("sector_move") is not None else ""
    )

    cards = ""
    for r in report["results"]:
        p    = r["price_data"]
        up   = p["pct_change"] >= 0
        clr  = "#2e7d32" if up else "#c62828"
        bg   = "#f1f8e9" if up else "#ffebee"
        conf = r["confidence"]

        # Top events that drove the analysis
        ev_rows = "".join(
            f"<tr><td style='color:#888;font-size:11px;white-space:nowrap;padding:3px 8px 3px 0'>"
            f"{e['time_str']}</td>"
            f"<td style='font-size:11px;padding:3px 6px 3px 0'>"
            f"<span style='background:#eee;border-radius:3px;padding:1px 4px;font-size:10px;"
            f"text-transform:uppercase'>{e['type']}</span></td>"
            f"<td style='font-size:12px;color:#333;padding:3px 0'>{e['title']}</td></tr>"
            for e in r["top_events"]
        ) or "<tr><td colspan='3' style='color:#aaa;font-size:12px'>No material events in window</td></tr>"

        cards += f"""
<div style="border:1px solid #e0e0e0;border-radius:10px;overflow:hidden;
            margin-bottom:28px;font-family:Arial,sans-serif">

  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;
              align-items:flex-start;padding:18px 20px;background:{bg}">
    <div>
      <div style="font-size:18px;font-weight:700;margin-bottom:2px">
        {r['stock']['name']}
        <span style="font-size:12px;color:#666;font-weight:400;margin-left:6px">
          {r['stock']['ticker']}
        </span>
      </div>
      <span style="display:inline-block;background:{CONF_BG[conf]};color:{CONF_COLOR[conf]};
                   border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700">
        Confidence: {conf}
      </span>
    </div>
    <div style="text-align:right">
      <div style="font-size:26px;font-weight:700;color:{clr}">${p['price']}</div>
      <div style="color:{clr};font-size:14px;font-weight:600">
        {'▲' if up else '▼'} {abs(p['pct_change']):.1f}%
      </div>
      <div style="color:#888;font-size:11px">
        Range: ${p['day_low']} – ${p['day_high']}
      </div>
    </div>
  </div>

  <!-- AI summary -->
  <div style="padding:14px 20px;font-size:14px;line-height:1.7;
              background:#fafafa;border-top:1px solid #eee;border-bottom:1px solid #eee">
    {r['summary']}
  </div>

  <!-- Event timeline -->
  <div style="padding:12px 20px">
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                color:#999;margin-bottom:8px;letter-spacing:.5px">
      Evidence used
    </div>
    <table style="width:100%;border-collapse:collapse">{ev_rows}</table>
  </div>

</div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;
                                  max-width:680px;margin:auto;padding:24px;
                                  background:#f5f5f5">
  <div style="background:#fff;border-radius:10px;padding:24px;
              box-shadow:0 1px 4px rgba(0,0,0,.1)">
    <h2 style="margin:0 0 4px;font-size:20px">📊 Shadow Coverage Daily Brief</h2>
    <p style="color:#888;font-size:12px;margin:0 0 20px">
      {report['date']} · 11:00am AEST &nbsp;·&nbsp; {sector_line}
    </p>
    {cards}
    <p style="color:#ccc;font-size:10px;margin-top:16px">
      Automated summary — verify before acting. Confidence reflects quality of available evidence.
    </p>
  </div>
</body></html>"""

def send():
    with open("report.json") as f:
        report = json.load(f)
    html = build_html(report)

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"{EMAIL_SUBJECT} — {report['date']}"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT
    msg.attach(MIMEText(html, "html"))

    pwd = os.environ["GMAIL_APP_PASSWORD"]
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_SENDER, pwd)
        s.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
    print(f"✓ Email sent to {EMAIL_RECIPIENT}")

if __name__ == "__main__":
    send()
