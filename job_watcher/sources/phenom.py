"""Phenom career sites, e.g. careers.bcg.com.

Phenom pages embed their config and first page of results in the HTML
(`phApp` and `phApp.ddo.eagerLoadRefineSearch`), and load the rest from a
public JSON endpoint the page itself calls:

    POST https://<site>/widgets   {"ddoKey": "refineSearch", "selected_fields": {...}, ...}

Strategy:
  1. GET the search page once to read the site config (refNum, locale).
  2. POST to /widgets with server-side facets (e.g. country: India), 100 per page.
  3. If the widgets call fails or returns an unexpected shape, fall back to
     paging the HTML search page per keyword (10 jobs per page, filtered locally).

Config:
    source: phenom
    url: https://careers.bcg.com/global/en
    facets: {country: [India]}            # server-side filter for step 2
    search: [associate, analyst]          # keywords used only by the fallback
"""

from __future__ import annotations

import json
import re

from ..models import Job

PH_APP = re.compile(r"phApp\s*=\s*phApp\s*\|\|\s*(\{.*?\});", re.S)
PH_DDO = re.compile(r"phApp\.ddo\s*=\s*(\{.*?\});\s*phApp", re.S)
WIDGET_SIZE = 100
PAGE_SIZE = 10


def parse_page(html: str) -> tuple[dict, dict]:
    """Return (site config, eagerLoadRefineSearch block) from a Phenom page."""
    app = PH_APP.search(html)
    ddo = PH_DDO.search(html)
    cfg = json.loads(app.group(1)) if app else {}
    eager = json.loads(ddo.group(1)).get("eagerLoadRefineSearch", {}) if ddo else {}
    return cfg, eager


def to_job(j: dict, base: str, company: str) -> Job:
    locs = j.get("multi_location") or [j.get("location") or j.get("cityStateCountry") or ""]
    location = "; ".join(l for l in locs if l)
    if j.get("country") and j["country"] not in location:
        location = f"{location} ({j['country']})" if location else j["country"]
    jid = str(j.get("jobId") or j.get("reqId") or j.get("jobSeqNo"))
    return Job(
        company=company,
        job_id=jid,
        title=(j.get("title") or "").strip(),
        location=location,
        url=f"{base}/job/{jid}",
        posted=(j.get("postedDate") or "")[:10],
        source="phenom",
    )


def _via_widgets(session, base: str, origin: str, site: dict, cfg: dict) -> list[Job]:
    endpoint = site.get("widgetApiEndpoint") or f"{origin}/widgets"
    max_pages = int(cfg.get("max_pages", 10))
    jobs: list[Job] = []
    for page in range(max_pages):
        body = {
            "lang": site.get("locale", "en_global"),
            "deviceType": "desktop",
            "country": site.get("country", "global"),
            "pageName": "search-results",
            "ddoKey": "refineSearch",
            "sortBy": "Most recent",
            "subsearch": "",
            "from": page * WIDGET_SIZE,
            "jobs": True,
            "counts": True,
            "all_fields": list((cfg.get("facets") or {}).keys()),
            "size": WIDGET_SIZE,
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": False,
            "pageId": site.get("pageId", "page"),
            "siteType": site.get("siteType", "external"),
            "keywords": "",
            "global": True,
            "selected_fields": cfg.get("facets") or {},
            "locationData": {},
        }
        resp = session.post(endpoint, json=body, timeout=30,
                            headers={"Accept": "application/json", "Content-Type": "application/json"})
        resp.raise_for_status()
        block = resp.json().get("refineSearch") or {}
        batch = (block.get("data") or {}).get("jobs")
        if batch is None:
            raise ValueError("unexpected widgets response shape")
        jobs.extend(to_job(j, base, cfg["name"]) for j in batch)
        total = block.get("totalHits") or 0
        if not batch or len(jobs) >= total:
            break
    return jobs


def _via_pages(session, base: str, cfg: dict) -> list[Job]:
    terms = cfg.get("search") or [""]
    if isinstance(terms, str):
        terms = [terms]
    max_pages = int(cfg.get("fallback_max_pages", 15))
    merged: dict[str, Job] = {}
    for term in terms:
        for page in range(max_pages):
            resp = session.get(f"{base}/search-results",
                               params={"keywords": term, "from": page * PAGE_SIZE, "s": 1}, timeout=30)
            resp.raise_for_status()
            _, eager = parse_page(resp.text)
            batch = (eager.get("data") or {}).get("jobs") or []
            for j in batch:
                job = to_job(j, base, cfg["name"])
                merged.setdefault(job.job_id, job)
            if not batch or (page + 1) * PAGE_SIZE >= (eager.get("totalHits") or 0):
                break
    return list(merged.values())


def fetch(cfg: dict, session) -> list[Job]:
    base = cfg["url"].rstrip("/")
    origin = "/".join(base.split("/")[:3])
    resp = session.get(f"{base}/search-results", timeout=30)
    resp.raise_for_status()
    site, _ = parse_page(resp.text)
    try:
        return _via_widgets(session, base, origin, site, cfg)
    except Exception as e:
        print(f"[{cfg['name']}] Phenom widgets call failed ({type(e).__name__}); using page search fallback")
        return _via_pages(session, base, cfg)
