"""Phenom adapter (BCG). The fixture is a trimmed copy of the live BCG
search page captured Nov 2026: real site config + 10 real job records."""

from conftest import FakeResponse, FakeSession, load_text

from job_watcher.sources import phenom

BASE = "https://careers.bcg.com/global/en"
CFG = {"name": "BCG", "url": BASE, "facets": {"country": ["India"]}, "search": ["associate"]}


def india_job(i):
    return {"jobId": f"IN{i}", "title": f"Associate {i}", "country": "India",
            "multi_location": ["Mumbai, Maharashtra, India", "New Delhi, Delhi, India"], "postedDate": "2026-11-01T00:00:00.000+0000"}


def test_parse_real_bcg_page():
    site, eager = phenom.parse_page(load_text("phenom_bcg.html"))
    assert site["refNum"] == "BCG1US"
    assert site["widgetApiEndpoint"] == "https://careers.bcg.com/widgets"
    jobs = [phenom.to_job(j, BASE, "BCG") for j in eager["data"]["jobs"]]
    assert len(jobs) == 10
    assert jobs[0].title == "Associate, Experienced Hire, United States"
    assert jobs[0].url == f"{BASE}/job/58355"
    assert "Boston, Massachusetts" in jobs[0].location


def test_widgets_call_sends_india_facet_and_paginates():
    def widgets(kw):
        start = kw["json"]["from"]
        n = 100 if start == 0 else 12
        return FakeResponse({"refineSearch": {"status": 200, "totalHits": 112,
                                              "data": {"jobs": [india_job(start + i) for i in range(n)]}}})

    s = FakeSession({f"{BASE}/search-results": load_text("phenom_bcg.html"),
                     "https://careers.bcg.com/widgets": widgets})
    jobs = phenom.fetch(CFG, s)
    assert len(jobs) == 112
    posts = [c for c in s.calls if c[0] == "POST"]
    assert len(posts) == 2
    body = posts[0][2]["json"]
    assert body["selected_fields"] == {"country": ["India"]}
    assert body["ddoKey"] == "refineSearch" and body["size"] == 100
    assert jobs[0].location == "Mumbai, Maharashtra, India; New Delhi, Delhi, India"


def test_falls_back_to_page_search_when_widgets_fails():
    s = FakeSession({f"{BASE}/search-results": load_text("phenom_bcg.html")})  # /widgets -> 404
    jobs = phenom.fetch(CFG, s)
    assert len(jobs) == 10
    gets = [c for c in s.calls if c[0] == "GET" and c[2].get("params")]
    assert gets[0][2]["params"] == {"keywords": "associate", "from": 0, "s": 1}
