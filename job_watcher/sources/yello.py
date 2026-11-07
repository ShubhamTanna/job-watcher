"""Yello (recsolu.com) job boards, e.g. Kearney.

The board's search endpoint returns JSON with an HTML fragment of results:
    GET https://<tenant>.recsolu.com/job_boards/<board_id>/search?query=&filters=&page_number=N
    -> {"html": "<li ...>", "more_requisitions": true, ...}

Config:
    source: yello
    url: https://kearney.recsolu.com/job_boards/EPd41qlA4_03IncZMnWyRQ

Find the long board id in the page source (data-search-url) or the og:url tag.
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import Job


def parse_results(html: str, origin: str, company: str) -> list[Job]:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for li in soup.select("li.search-results__item"):
        a = li.select_one("a.search-results__req_title")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        job_id = href.split("/jobs/")[-1].split("?")[0]
        info = [s.get_text(" ", strip=True) for s in li.select(".search-results__jobinfo div span")]
        # spans are [job type, region, cities]; keep region + cities as location
        location = ", ".join(x for x in info[1:] if x)
        posted = li.select_one(".search-results__post-time")
        jobs.append(
            Job(
                company=company,
                job_id=job_id,
                title=a.get_text(" ", strip=True),
                location=location,
                url=href if href.startswith("http") else origin + href,
                posted=posted.get_text(strip=True) if posted else "",
                source="yello",
            )
        )
    return jobs


def fetch(cfg: dict, session) -> list[Job]:
    board = cfg["url"].rstrip("/")
    parsed = urlparse(board)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    max_pages = int(cfg.get("max_pages", 15))
    jobs: list[Job] = []
    for page in range(1, max_pages + 1):
        resp = session.get(
            f"{board}/search",
            params={"query": "", "filters": "", "page_number": page},
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = parse_results(data.get("html", ""), origin, cfg["name"])
        jobs.extend(batch)
        if not batch or not data.get("more_requisitions"):
            break
    return jobs
