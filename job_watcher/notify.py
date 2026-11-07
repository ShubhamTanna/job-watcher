"""Alert channels. Each channel turns itself on only if its secrets are set,
so you can run Telegram, email, both, or neither (console only).

GitHub:   ALERT_GITHUB_ISSUE=true plus GITHUB_TOKEN and GITHUB_REPOSITORY (both
          provided automatically inside GitHub Actions). Opens one issue per
          day with new matches; GitHub emails it and pushes it to the GitHub app.
Telegram: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Email:    SMTP_USER, SMTP_PASSWORD (a Gmail App Password, not your login),
          ALERT_EMAIL_TO (defaults to SMTP_USER), SMTP_HOST, SMTP_PORT
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from html import escape

from .models import Job

TELEGRAM_LIMIT = 4000  # API hard limit is 4096 chars per message


def build_digest(new_matches: list[Job], errors: list[str], baseline_companies: list[str]) -> list[str]:
    """Return digest lines grouped by company (Telegram HTML subset)."""
    lines: list[str] = []
    if new_matches:
        lines.append(f"<b>{len(new_matches)} new matching role(s)</b>")
        by_company: dict[str, list[Job]] = {}
        for j in new_matches:
            by_company.setdefault(j.company, []).append(j)
        for company, jobs in sorted(by_company.items()):
            tag = " (first run: current openings)" if company in baseline_companies else ""
            lines.append(f"\n<b>{escape(company)}</b>{tag}")
            for j in jobs:
                loc = f" | {escape(j.location)}" if j.location else ""
                lines.append(f'• <a href="{escape(j.url)}">{escape(j.title)}</a>{loc}')
    if errors:
        lines.append("\n<b>Sources that failed today</b>")
        lines.extend(f"• {escape(e)}" for e in errors)
    return lines


def _chunks(lines: list[str], limit: int) -> list[str]:
    out, cur = [], ""
    for line in lines:
        if len(cur) + len(line) + 1 > limit:
            out.append(cur)
            cur = ""
        cur += line + "\n"
    if cur:
        out.append(cur)
    return out


def send_telegram(lines: list[str], session) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    for chunk in _chunks(lines, TELEGRAM_LIMIT):
        r = session.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": chunk, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=30,
        )
        r.raise_for_status()
    return True


ISSUE_BODY_LIMIT = 60000  # GitHub caps issue bodies at 65,536 chars


def _md(text: str) -> str:
    """Escape characters that would break a markdown link label."""
    return text.replace("[", "(").replace("]", ")").replace("|", "/")


def build_markdown(new_matches: list[Job], errors: list[str], baseline_companies: list[str]) -> str:
    out: list[str] = []
    if new_matches:
        by_company: dict[str, list[Job]] = {}
        for j in new_matches:
            by_company.setdefault(j.company, []).append(j)
        for company, jobs in sorted(by_company.items()):
            tag = " _(first run: current openings)_" if company in baseline_companies else ""
            out.append(f"\n### {company} ({len(jobs)}){tag}")
            for j in jobs:
                loc = f" — {j.location}" if j.location else ""
                out.append(f"- [{_md(j.title)}]({j.url}){_md(loc)}")
    if errors:
        out.append("\n### Sources that failed today")
        out.extend(f"- {e}" for e in errors)
    body = "\n".join(out).strip()
    if len(body) > ISSUE_BODY_LIMIT:
        body = body[:ISSUE_BODY_LIMIT].rsplit("\n", 1)[0] + "\n\n_…truncated; full list in data/history.csv_"
    return body


def send_github_issue(new_matches, errors, baseline_companies, subject: str, session) -> bool:
    if os.getenv("ALERT_GITHUB_ISSUE", "").lower() not in ("1", "true", "yes"):
        return False
    token, repo = os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_REPOSITORY")
    if not (token and repo):
        return False
    owner = os.getenv("GITHUB_REPOSITORY_OWNER") or repo.split("/")[0]
    body = build_markdown(new_matches, errors, baseline_companies)
    # The @mention guarantees a notification even if repo watching is turned off.
    body += f"\n\n---\ncc @{owner} · close this issue once you've reviewed it"
    labels = ["new-jobs"] if new_matches else ["source-errors"]
    r = session.post(
        f"https://api.github.com/repos/{repo}/issues",
        json={"title": subject, "body": body, "labels": labels},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    r.raise_for_status()
    return True


def send_email(lines: list[str], subject: str) -> bool:
    user, pw = os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if not (user and pw):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = os.getenv("ALERT_EMAIL_TO") or user
    msg.set_content("HTML email - open in a mail client that renders HTML.")
    msg.add_alternative("<br>".join(lines), subtype="html")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, timeout=30) as s:
        s.login(user, pw)
        s.send_message(msg)
    return True
