"""Workday careers sites (the *.myworkdayjobs.com portals many large firms use).

The page itself is rendered by JavaScript, but it loads jobs from a JSON
endpoint we can call directly:

    POST https://<host>/wday/cxs/<tenant>/<site>/jobs

Config needs the careers URL, e.g.
    url: https://acme.wd5.myworkdayjobs.com/en-US/AcmeCareers
From that we derive host=acme.wd5.myworkdayjobs.com, tenant=acme, site=AcmeCareers.

Portal-side filters: any query parameters on the URL (copied from the
browser after ticking filters on the careers page, e.g.
?locationCountry=<id>) are sent as Workday "appliedFacets". If Workday
rejects them, the run retries once without them and filters locally instead.

search: a term or a list of terms. Each term is a separate server-side search;
results are merged and de-duplicated. Leave it out to list everything.

Workday pages are capped at 20 results, so each search paginates up to max_pages.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from ..models import Job

PAGE_SIZE = 20
MULTI_LOCATION = re.compile(r"^\d+\s+locations?$", re.I)


def parse_url(url: str) -> tuple[str, str, str]:
    """Return (host, tenant, site) from a Workday careers URL."""
    parsed = urlparse(url)
    host = parsed.netloc
    tenant = host.split(".")[0]
    parts = [p for p in parsed.path.split("/") if p]
    # Drop a leading locale segment like "en-US"
    if parts and len(parts[0]) == 5 and parts[0][2] == "-":
        parts = parts[1:]
    if not parts:
        raise ValueError(f"Can't find the Workday site name in {url}")
    return host, tenant, parts[0]


def facets_from_url(url: str) -> dict[str, list[str]]:
    return {k: v for k, v in parse_qs(urlparse(url).query).items() if v}


def _search(session, api: str, host: str, site: str, cfg: dict, term: str, facets: dict) -> list[Job]:
    max_pages = int(cfg.get("max_pages", 10))
    jobs: list[Job] = []
    offset, total = 0, None
    for _ in range(max_pages):
        body = {"appliedFacets": facets, "limit": PAGE_SIZE, "offset": offset, "searchText": term}
        resp = session.post(api, json=body, timeout=30, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        if total is None:
            total = data.get("total", 0)
        postings = data.get("jobPostings", [])
        for p in postings:
            path = p.get("externalPath", "")
            bullets = p.get("bulletFields") or []
            loc = (p.get("locationsText") or "").strip()
            jobs.append(
                Job(
                    company=cfg["name"],
                    job_id=str(bullets[0] if bullets else path),
                    title=p.get("title", "").strip(),
                    # "3 Locations" says nothing; blank means "unknown", which the
                    # location filter keeps rather than silently dropping.
                    location="" if MULTI_LOCATION.match(loc) else loc,
                    url=f"https://{host}/{site}{path}",
                    posted=p.get("postedOn", ""),
                    source="workday",
                )
            )
        offset += PAGE_SIZE
        if not postings or offset >= (total or 0):
            break
    return jobs


def fetch(cfg: dict, session) -> list[Job]:
    host, tenant, site = parse_url(cfg["url"])
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    facets = facets_from_url(cfg["url"])
    terms = cfg.get("search") or [""]
    if isinstance(terms, str):
        terms = [terms]

    merged: dict[str, Job] = {}
    for term in terms:
        try:
            found = _search(session, api, host, site, cfg, term, facets)
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if not facets or status not in (400, 422):
                raise
            print(f"[{cfg['name']}] Workday rejected the URL filters ({status}); retrying without them")
            facets = {}
            found = _search(session, api, host, site, cfg, term, facets)
        for j in found:
            merged.setdefault(j.job_id, j)
    return list(merged.values())
