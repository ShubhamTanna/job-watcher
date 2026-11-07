"""Ashby public job board API.

Find the board name in the careers URL: jobs.ashbyhq.com/<name>.
"""

from __future__ import annotations

from ..models import Job

API = "https://api.ashbyhq.com/posting-api/job-board/{name}"


def fetch(cfg: dict, session) -> list[Job]:
    resp = session.get(API.format(name=cfg["board"]), timeout=30)
    resp.raise_for_status()
    jobs = []
    for j in resp.json().get("jobs", []):
        if j.get("isListed") is False:
            continue
        locations = [j.get("location", "")]
        locations += [s.get("location", "") for s in j.get("secondaryLocations") or []]
        url = j.get("jobUrl", "")
        jobs.append(
            Job(
                company=cfg["name"],
                job_id=str(j.get("id") or url),
                title=j.get("title", "").strip(),
                location=", ".join(l for l in locations if l),
                url=url,
                posted=(j.get("publishedAt") or "")[:10],
                source="ashby",
            )
        )
    return jobs
