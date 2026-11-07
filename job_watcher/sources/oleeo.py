"""Oleeo (tal.net) job boards, e.g. L.E.K. Consulting.

The listing page is server-rendered HTML, so we parse it directly.

Config:
    source: oleeo
    url: https://lek.tal.net/vx/lang-en-GB/mobile-0/appcentre-3/brand-2/candidate/jobboard/vacancy/5/adv/

Only the first results page is read. That covers boards with a few dozen
openings (L.E.K. Asia lists ~12); a large board would need pagination added.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ..models import Job


def _field(tile, cls: str) -> str:
    el = tile.select_one(cls)
    if not el:
        return ""
    label = el.select_one(".candidate-opp-field-label")
    if label:
        label.extract()
    return el.get_text(" ", strip=True)


def parse(html: str, company: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for li in soup.select("li.opp-container[data-oppid]"):
        a = li.select_one("a.subject")
        if not a:
            continue
        closing = _field(li, ".candidate-opp-field-4")
        jobs.append(
            Job(
                company=company,
                job_id=li["data-oppid"],
                title=a.get_text(" ", strip=True),
                location=_field(li, ".candidate-opp-field-3"),
                url=a.get("href", ""),
                posted=f"closes {closing}" if closing else "",
                source="oleeo",
            )
        )
    return jobs


def fetch(cfg: dict, session) -> list[Job]:
    resp = session.get(cfg["url"], timeout=30)
    resp.raise_for_status()
    return parse(resp.text, cfg["name"])
