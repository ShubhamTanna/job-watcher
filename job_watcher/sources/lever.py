"""Lever public postings API.

Find the company slug in the careers URL: jobs.lever.co/<slug>.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Job

API = "https://api.lever.co/v0/postings/{slug}?mode=json"


def _ms_to_date(ms) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


def fetch(cfg: dict, session) -> list[Job]:
    resp = session.get(API.format(slug=cfg["board"]), timeout=30)
    resp.raise_for_status()
    jobs = []
    for j in resp.json():
        cats = j.get("categories") or {}
        locations = cats.get("allLocations") or [cats.get("location", "")]
        jobs.append(
            Job(
                company=cfg["name"],
                job_id=str(j["id"]),
                title=j.get("text", "").strip(),
                location=", ".join(l for l in locations if l),
                url=j.get("hostedUrl", ""),
                posted=_ms_to_date(j.get("createdAt")),
                source="lever",
            )
        )
    return jobs
