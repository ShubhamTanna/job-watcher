"""iCIMS Jibe career sites (e.g. jobs.zs.com).

Jibe sites expose a public JSON search endpoint:
    GET https://<site>/api/jobs?page=1&limit=100

Config:
    source: jibe
    url: https://jobs.zs.com
"""

from __future__ import annotations

from ..models import Job

LIMIT = 100


def _location(d: dict) -> str:
    """Primary + additional locations, with countries so 'india' filters work."""
    raw = d.get("full_location") or d.get("short_location") or d.get("location_name") or ""
    parts = ["; ".join(dict.fromkeys(p.strip() for p in raw.split(";") if p.strip()))]  # dedupe
    countries = {d.get("country", "")}
    for extra in d.get("additional_locations") or []:
        countries.add(extra.get("country", ""))
    countries.discard("")
    if countries:
        parts.append("(" + ", ".join(sorted(countries)) + ")")
    return " ".join(p for p in parts if p).strip()


def fetch(cfg: dict, session) -> list[Job]:
    base = cfg["url"].rstrip("/")
    max_pages = int(cfg.get("max_pages", 10))
    jobs: list[Job] = []
    for page in range(1, max_pages + 1):
        resp = session.get(f"{base}/api/jobs", params={"page": page, "limit": LIMIT}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("jobs") or []
        for item in batch:
            d = item.get("data") or {}
            slug = d.get("slug") or d.get("req_id")
            jobs.append(
                Job(
                    company=cfg["name"],
                    job_id=str(d.get("req_id") or slug),
                    title=(d.get("title") or "").strip(),
                    location=_location(d),
                    url=f"{base}/jobs/{slug}",
                    posted=(d.get("posted_date") or "")[:10],
                    source="jibe",
                )
            )
        total = data.get("totalCount") or data.get("count") or 0
        if not batch or len(jobs) >= total:
            break
    return jobs
