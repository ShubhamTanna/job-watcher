"""Talemetry / Jobvite career sites, e.g. careers.alvarezandmarsal.com.

These sites expose their job search as JSON:
    GET https://<site>/search/jobs.json?page=1&location=India
    -> {"current_page": 1, "per_page": 25, "total_entries": 145, "entries": [...]}

Config:
    source: talemetry
    url: https://careers.alvarezandmarsal.com
    params: {location: India}     # optional, passed straight to the search
"""

from __future__ import annotations

from ..models import Job


def _location(loc: dict) -> str:
    loc = loc or {}
    parts = [loc.get("locality"), loc.get("country")]
    text = ", ".join(p for p in parts if p)
    if loc.get("name"):
        text = f"{text} ({loc['name']})" if text else loc["name"]
    return text


def fetch(cfg: dict, session) -> list[Job]:
    base = cfg["url"].rstrip("/")
    extra = cfg.get("params") or {}
    max_pages = int(cfg.get("max_pages", 20))
    jobs: list[Job] = []
    for page in range(1, max_pages + 1):
        resp = session.get(f"{base}/search/jobs.json", params={**extra, "page": page},
                           headers={"Accept": "application/json"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        entries = data.get("entries") or []
        for e in entries:
            jid = str(e.get("id"))
            slug = e.get("permalink")
            jobs.append(
                Job(
                    company=cfg["name"],
                    job_id=jid,
                    title=(e.get("title") or "").strip(),
                    location=_location(e.get("location")),
                    url=f"{base}/jobs/{jid}-{slug}" if slug else f"{base}/jobs/{jid}",
                    source="talemetry",
                )
            )
        total = data.get("total_entries") or 0
        if not entries or len(jobs) >= total:
            break
    return jobs
