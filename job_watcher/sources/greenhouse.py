"""Greenhouse public job board API.

Find the board token in the careers URL: boards.greenhouse.io/<token> or
job-boards.greenhouse.io/<token>.
"""

from __future__ import annotations

from ..models import Job

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch(cfg: dict, session) -> list[Job]:
    token = cfg["board"]
    resp = session.get(API.format(token=token), timeout=30)
    resp.raise_for_status()
    jobs = []
    for j in resp.json().get("jobs", []):
        jobs.append(
            Job(
                company=cfg["name"],
                job_id=str(j["id"]),
                title=j.get("title", "").strip(),
                location=(j.get("location") or {}).get("name", "").strip(),
                url=j.get("absolute_url", ""),
                posted=(j.get("updated_at") or "")[:10],
                source="greenhouse",
            )
        )
    return jobs
