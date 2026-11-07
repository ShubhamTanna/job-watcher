"""BearingPoint open-roles page (SuccessFactors behind it, rendered as HTML).

Config:
    source: bearingpoint
    url: https://www.bearingpoint.com/en-in/careers/open-roles/?country=IN

The page lists every opening for the chosen country in one response.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..models import Job


def parse(html: str, company: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs, seen = [], set()
    for a in soup.select('a.panel[href*="job-offer"]'):
        href = a["href"]
        job_id = (parse_qs(urlparse(href).query).get("id") or [href])[0]
        if job_id in seen:
            continue
        seen.add(job_id)
        title = a.select_one(".panel-header")
        loc = a.select_one(".job-info")
        jobs.append(
            Job(
                company=company,
                job_id=job_id,
                title=title.get_text(" ", strip=True) if title else "",
                location=loc.get_text(" ", strip=True) if loc else "",
                url=href,
                source="bearingpoint",
            )
        )
    return jobs


def fetch(cfg: dict, session) -> list[Job]:
    resp = session.get(cfg["url"], timeout=30)
    resp.raise_for_status()
    return parse(resp.text, cfg["name"])
