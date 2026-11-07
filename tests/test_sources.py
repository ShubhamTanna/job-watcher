from conftest import FakeResponse, FakeSession, load

from job_watcher.sources import ashby, greenhouse, lever, workday


def test_greenhouse_parses_jobs():
    s = FakeSession({"https://boards-api.greenhouse.io/v1/boards/acme/jobs": load("greenhouse.json")})
    jobs = greenhouse.fetch({"name": "Acme", "board": "acme"}, s)
    assert len(jobs) == 4
    j = jobs[0]
    assert (j.job_id, j.title, j.location, j.posted) == ("101", "Business Analyst", "Mumbai, India", "2026-10-15")
    assert j.key == "Acme::101"


def test_lever_joins_all_locations():
    s = FakeSession({"https://api.lever.co/v0/postings/beta": load("lever.json")})
    jobs = lever.fetch({"name": "Beta", "board": "beta"}, s)
    assert jobs[0].location == "Bengaluru, Mumbai"
    assert jobs[0].posted == "2025-10-09"
    assert jobs[1].location == "Mumbai"


def test_ashby_skips_unlisted():
    s = FakeSession({"https://api.ashbyhq.com/posting-api/job-board/gamma": load("ashby.json")})
    jobs = ashby.fetch({"name": "Gamma", "board": "gamma"}, s)
    assert [j.job_id for j in jobs] == ["c1"]


def test_workday_url_parsing():
    assert workday.parse_url("https://acme.wd5.myworkdayjobs.com/en-US/AcmeCareers") == (
        "acme.wd5.myworkdayjobs.com", "acme", "AcmeCareers")
    assert workday.parse_url("https://acme.wd1.myworkdayjobs.com/External/") == (
        "acme.wd1.myworkdayjobs.com", "acme", "External")


def test_workday_paginates_until_total():
    def page(kw):
        offset = kw["json"]["offset"]
        n = 20 if offset < 40 else 5  # 45 jobs total across 3 pages
        postings = [
            {"title": f"Analyst {offset + i}", "externalPath": f"/job/Mumbai/Analyst_R{offset + i}",
             "locationsText": "Mumbai", "postedOn": "Posted Today", "bulletFields": [f"R{offset + i}"]}
            for i in range(n)
        ]
        return FakeResponse({"total": 45, "jobPostings": postings})

    s = FakeSession({"https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Ext/jobs": page})
    jobs = workday.fetch({"name": "Acme", "url": "https://acme.wd5.myworkdayjobs.com/en-US/Ext", "search": "analyst"}, s)
    assert len(jobs) == 45
    assert len(s.calls) == 3
    assert s.calls[0][2]["json"]["searchText"] == "analyst"
    assert jobs[0].url == "https://acme.wd5.myworkdayjobs.com/Ext/job/Mumbai/Analyst_R0"
    assert jobs[0].job_id == "R0"


def test_workday_respects_max_pages():
    def page(kw):
        return FakeResponse({"total": 1000, "jobPostings": [
            {"title": "X", "externalPath": f"/job/{kw['json']['offset']}_{i}", "bulletFields": []} for i in range(20)]})

    s = FakeSession({"https://a.wd1.myworkdayjobs.com/wday/cxs/a/S/jobs": page})
    jobs = workday.fetch({"name": "A", "url": "https://a.wd1.myworkdayjobs.com/S", "max_pages": 2}, s)
    assert len(jobs) == 40
