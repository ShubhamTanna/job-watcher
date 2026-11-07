"""Persistent state, stored as plain files in the repo so GitHub Actions can
commit them back after each run.

data/seen.json    {"jobs": {job_key: first_seen}, "companies": {name: {...}}}
                  jobs drives the diff; companies tracks which boards have
                  been fetched successfully at least once (baseline detection)
data/history.csv  every posting ever observed, matched or not: the dataset
                  for hiring-trend analysis later
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Job

HISTORY_FIELDS = ["first_seen", "company", "job_id", "title", "location", "url", "posted", "source", "matched"]


class State:
    def __init__(self, data_dir: str | Path):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.seen_path = self.dir / "seen.json"
        self.history_path = self.dir / "history.csv"
        raw = {}
        if self.seen_path.exists():
            raw = json.loads(self.seen_path.read_text() or "{}")
        self.jobs: dict[str, str] = raw.get("jobs", {})
        self.companies: dict[str, dict] = raw.get("companies", {})

    def is_new(self, job: Job) -> bool:
        return job.key not in self.jobs

    def is_tracked(self, company: str) -> bool:
        return company in self.companies

    def mark_company(self, company: str, listed: int, today: str) -> None:
        entry = self.companies.setdefault(company, {"first_run": today})
        entry.update({"last_run": today, "last_listed": listed})

    def record(self, jobs: list[tuple[Job, bool]], today: str) -> None:
        """Mark jobs as seen and append them to history. jobs = [(job, matched)]."""
        if not jobs:
            return
        new_file = not self.history_path.exists()
        with self.history_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
            if new_file:
                w.writeheader()
            for job, matched in jobs:
                self.jobs[job.key] = today
                w.writerow({"first_seen": today, **job.to_dict(), "matched": int(matched)})

    def save(self) -> None:
        payload = {"jobs": self.jobs, "companies": self.companies}
        self.seen_path.write_text(json.dumps(payload, indent=1, sort_keys=True))
