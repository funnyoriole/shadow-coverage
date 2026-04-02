import json, os, smtplib, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import EMAIL_SUBJECT_MACRO

SENDER    = os.environ["GMAIL_SENDER_MACRO"]
RECIPIENT = os.environ["GMAIL_RECIPIENT"]
PASSWORD  = os.environ["GMAIL_APP_PASSWORD_MACRO"]

def md_to_html(text: str) -> str:
    """Minimal markdown → HTML: headers and [KEY] highlights only."""
    lines  = text.split("\n")
    output = []
    for line in lines:
        # ## Section header
        if line.startswith("## "):
            heading = line[3:].strip()
            output.append(
                f"<h3 style='margin:20px 0 6px;font-size:14px;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:.5px;color:#555;"
                f"border-bottom:1px solid #eee;padding-bottom:4px'>{heading}</h3>"
            )
        # [KEY] highlighted sentence
        elif "[KEY]" in line:
            highlighted = line.replace(
                "[KEY]",
                "<span style='background:#fff3cd;padding:1px 5px;border-radius:3px;"
                "font-weight:700;font-size:11px;margin-right:4px'>KEY</span>"
            )
            output.append(
                f"<p style='margin:4px 0;font-size:13px;line-height:1.6;"
                f"background:#fffdf0;padding:6px 8px;border-radius:4px;"
                f"border-left:3px solid #f0c040'>{highlighted}</p>"
            )
        elif line.strip():
            output.append(
                f"<p style='margin:4px 0;font-size:13px;line-height:1.6;color:#333'>{line}</p>"
            )
    return "\n".join(output)

def format_snapshot_html(snapshot: list) -> str:
    rows = ""
    for r in snapshot:
        up  = r["pct"] >= 0
        clr = "#2e7d32" if up else "#c62828"
        rows += (
            f"<tr>"
            f"<td style='padding:4px 12px 4px 0;font-size:12px;color:#555'>{r['name']}</td>"
            f"<td style='padding:4px 12px 4px 0;font-size:12px;font-weight:600'>{r['price']:,.2f}</td>"
            f"<td style='padding:4px 0;font-size:12px;color:{clr};font-weight:600'>"
            f"{'▲' if up else '▼'} {abs(r['pct']):.1f}%</td>"
            f"</tr>"
        )
    return f"<table style='border-collapse:collapse;margin-bottom:8px'>{rows}</table>"

def build_html(report: dict) -> str:
    snapshot_html = format_snapshot_html(report["snapshot"])
    brief_html    = md_to_html(report["brief"])

    return f"""<html><body style="font-family:Arial,sans-serif;max-width:680px;
                                  margin:auto;padding:24px;background:#f5f5f5">
  <div style="background:#fff;border-radius:10px;padding:24px;
              box-shadow:0 1px 4px rgba(0,0,0,.1)">

    <h2 style="margin:0 0 2px;font-size:20px">🌏 Morning Intelligence Brief</h2>
    <p style="color:#888;font-size:12px;margin:0 0 20px">{report['date']} · 8:00am AEST</p>

    <div style="background:#f8f8f8;border-radius:8px;padding:14px 16px;margin-bottom:20px">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;
                  color:#999;letter-spacing:.5px;margin-bottom:10px">
        Market snapshot
      </div>
      {snapshot_html}
    </div>

    {brief_html}

    <p style="color:#ccc;font-size:10px;margin-top:24px">
      Auto-generated morning brief — verify before acting on any information.
    </p>
  </div>
</body></html>"""

def send():
    with open("macro_report.json") as f:
        report = json.load(f)

    html           = build_html(report)
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = f"{EMAIL_SUBJECT_MACRO} — {report['date']}"
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SENDER, PASSWORD)
        s.sendmail(SENDER, RECIPIENT, msg.as_string())
    print(f"✓ Macro brief sent to {RECIPIENT}")

if __name__ == "__main__":
    send()
