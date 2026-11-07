"""Daily run: fetch -> filter -> diff -> notify -> persist.

Usage:
    python -m job_watcher.main                 # normal run
    python -m job_watcher.main --dry-run       # print results, send nothing, save nothing
    python -m job_watcher.main --config other.yaml --data-dir data
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date

import requests
import yaml

from . import notify
from .filters import matches, rules_for
from .models import Job
from .sources import SOURCES, URL_SOURCES
from .state import State

USER_AGENT = "job-watcher/1.0 (personal job alert script; one request per board per day)"


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    companies = cfg.get("companies") or []
    if not companies:
        raise SystemExit(f"No companies listed in {path}")
    for c in companies:
        if c.get("source") not in SOURCES:
            raise SystemExit(f"{c.get('name')}: unknown source '{c.get('source')}'. Use one of {sorted(SOURCES)}")
        needed = "url" if c["source"] in URL_SOURCES else "board"
        if not c.get(needed):
            raise SystemExit(f"{c.get('name')}: '{c['source']}' source needs a '{needed}' field")
    return cfg


def _redact(msg: str) -> str:
    """Keep secrets (e.g. a bot token inside a URL) out of logs and alerts."""
    return re.sub(r"bot\d+:[\w-]+", "bot<redacted>", msg)


def run(config_path: str, data_dir: str, dry_run: bool = False, session=None) -> int:
    cfg = load_config(config_path)
    session = session or requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    state = State(data_dir)
    today = date.today().isoformat()

    new_matches: list[Job] = []
    to_record: list[tuple[Job, bool]] = []
    errors: list[str] = []
    baseline: list[str] = []
    failures = 0

    for company in cfg["companies"]:
        name = company["name"]
        if company.get("enabled") is False:
            continue
        try:
            jobs = SOURCES[company["source"]](company, session)
        except Exception as e:  # one broken portal shouldn't kill the whole run
            failures += 1
            errors.append(f"{name}: {_redact(type(e).__name__ + ': ' + str(e))[:200]}")
            continue

        first_run = not state.is_tracked(name)
        if first_run:
            if jobs:
                baseline.append(name)
            else:
                errors.append(f"{name}: returned 0 jobs on first run. Check the board/url in config.")
        state.mark_company(name, len(jobs), today)

        rules = rules_for(company, cfg.get("filters") or {})
        hits = 0
        for job in jobs:
            if not state.is_new(job):
                continue
            ok = matches(job, rules)
            to_record.append((job, ok))
            if ok:
                new_matches.append(job)
                hits += 1
        print(f"[{name}] {len(jobs)} listed, {hits} new matches")

    lines = notify.build_digest(new_matches, errors, baseline)
    print("\n".join(lines) or "Nothing new today.")

    if dry_run:
        print("\n(dry run: no alerts sent, no state saved)")
        return 0

    if lines:
        subject = (f"{len(new_matches)} new role(s) · {today}" if new_matches
                   else f"Job watcher: source errors · {today}")
        try:
            sent = [
                notify.send_github_issue(new_matches, errors, baseline, subject, session),
                notify.send_telegram(lines, session),
                notify.send_email(lines, subject),
            ]
            if not any(sent):
                print("No alert channel configured. Set Telegram or SMTP secrets to get alerts.")
        except Exception as e:
            # Don't mark jobs as seen if the alert never went out; they'll retry tomorrow.
            print(f"Alert failed, state not saved: {_redact(str(e))}", file=sys.stderr)
            return 1

    state.record(to_record, today)
    state.save()

    if failures and failures == sum(1 for c in cfg["companies"] if c.get("enabled") is not False):
        print("Every source failed.", file=sys.stderr)
        return 1
    return 0


def cli() -> None:
    p = argparse.ArgumentParser(description="Daily job-portal watcher")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    sys.exit(run(a.config, a.data_dir, a.dry_run))


if __name__ == "__main__":
    cli()
