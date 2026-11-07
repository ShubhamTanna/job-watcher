"""Adapters added for the consulting-firm portals. Fixtures are trimmed copies
of real responses captured from each live site in Nov 2026."""

from conftest import FakeResponse, FakeSession, load, load_text

from job_watcher.filters import matches
from job_watcher.sources import bearingpoint, jibe, oleeo, talemetry, workday, yello

ZS = "https://jobs.zs.com"
KEARNEY = "https://kearney.recsolu.com/job_boards/EPd41qlA4_03IncZMnWyRQ"
AM = "https://careers.alvarezandmarsal.com"
LEK = "https://lek.tal.net/vx/lang-en-GB/mobile-0/appcentre-3/brand-2/candidate/jobboard/vacancy/5/adv/"
BP = "https://www.bearingpoint.com/en-in/careers/open-roles/?country=IN"


def test_jibe_parses_real_zs_response():
    s = FakeSession({f"{ZS}/api/jobs": load("jibe.json")})
    jobs = jibe.fetch({"name": "ZS", "url": ZS}, s)
    assert len(jobs) == 10
    j = jobs[0]
    assert j.title.startswith("Decision Analytics Associate Consultant")
    assert j.url == f"{ZS}/jobs/31533"
    assert "United States" in j.location  # country appended for location filtering
    assert s.calls[0][2]["params"] == {"page": 1, "limit": 100}


def test_jibe_paginates_until_total():
    def page(kw):
        p = kw["params"]["page"]
        n = 100 if p < 3 else 40
        return FakeResponse({"totalCount": 240, "jobs": [
            {"data": {"slug": f"{p}-{i}", "req_id": f"{p}-{i}", "title": "Analyst", "country": "India"}} for i in range(n)]})

    s = FakeSession({f"{ZS}/api/jobs": page})
    assert len(jibe.fetch({"name": "ZS", "url": ZS}, s)) == 240
    assert len(s.calls) == 3


def test_yello_parses_real_kearney_results():
    s = FakeSession({f"{KEARNEY}/search": load("yello_page.json")})
    jobs = yello.fetch({"name": "Kearney", "url": KEARNEY}, s)
    assert len(jobs) == 6
    j = jobs[0]
    assert j.title == "2027 Kearney Associate"
    assert j.location == "Asia Pacific, Bangkok, Jakarta, Kuala Lumpur, Singapore"
    assert j.url.startswith("https://kearney.recsolu.com/jobs/MhxR86A-URopW6iqpkGzbQ")
    assert j.job_id == "MhxR86A-URopW6iqpkGzbQ"


def test_yello_follows_more_requisitions():
    page1 = dict(load("yello_page.json"), more_requisitions=True)
    page2 = {"html": '<li class="search-results__item"><div class="search-results__jobinfo">'
                     '<a class="search-results__req_title" href="/jobs/ZZZ?job_board_id=x">Business Analyst</a>'
                     '<div><span>Full-time</span><span>Asia Pacific</span><span>Mumbai</span></div></div></li>',
             "more_requisitions": False}

    s = FakeSession({f"{KEARNEY}/search": lambda kw: FakeResponse(page1 if kw["params"]["page_number"] == 1 else page2)})
    jobs = yello.fetch({"name": "Kearney", "url": KEARNEY}, s)
    assert len(jobs) == 7
    assert [c[2]["params"]["page_number"] for c in s.calls] == [1, 2]
    assert jobs[-1].url == "https://kearney.recsolu.com/jobs/ZZZ?job_board_id=x"


def test_talemetry_parses_am_and_passes_params():
    s = FakeSession({f"{AM}/search/jobs.json": load("talemetry.json")})
    jobs = talemetry.fetch({"name": "A&M", "url": AM, "params": {"location": "India"}}, s)
    assert len(jobs) == 4
    assert jobs[1].url == f"{AM}/jobs/18191092-associate-pi-campus-global-capability-center"
    assert jobs[1].location == "Gurugram, India (IN-New Delhi GCC)"
    assert s.calls[0][2]["params"] == {"location": "India", "page": 1}


def test_oleeo_parses_lek_board():
    s = FakeSession({LEK: load_text("oleeo.html")})
    jobs = oleeo.fetch({"name": "L.E.K.", "url": LEK}, s)
    assert [j.job_id for j in jobs] == ["4149", "3914", "4162"]
    assert jobs[1].title == "Analyst/Senior Analyst (TMT)"
    assert jobs[1].location == "New Delhi"
    assert jobs[0].posted == "closes 23 Nov 2026 07:55 IST"


def test_bearingpoint_parses_real_page():
    s = FakeSession({BP: load_text("bearingpoint.html")})
    jobs = bearingpoint.fetch({"name": "BearingPoint", "url": BP}, s)
    assert len(jobs) == 9
    assert jobs[0].job_id == "T8578508"
    assert jobs[0].title == "Ivalua Senior Analyst / Consultant"
    assert jobs[0].location == "Bengaluru"


def test_workday_sends_url_filters_as_facets():
    url = "https://fticonsulting.wd108.myworkdayjobs.com/FTIConsultingCareers/?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e"
    api = "https://fticonsulting.wd108.myworkdayjobs.com/wday/cxs/fticonsulting/FTIConsultingCareers/jobs"
    s = FakeSession({api: {"total": 1, "jobPostings": [
        {"title": "Consultant", "externalPath": "/job/Mumbai/Consultant_R1", "locationsText": "2 Locations", "bulletFields": ["R1"]}]}})
    jobs = workday.fetch({"name": "FTI", "url": url}, s)
    assert s.calls[0][2]["json"]["appliedFacets"] == {"locationCountry": ["c4f78be1a8f14da0ab49ce1162348a5e"]}
    assert jobs[0].location == ""  # "2 Locations" carries no information
    assert jobs[0].url == "https://fticonsulting.wd108.myworkdayjobs.com/FTIConsultingCareers/job/Mumbai/Consultant_R1"


def test_workday_retries_without_rejected_facets():
    url = "https://mmc.wd1.myworkdayjobs.com/MMC?locationCountry=bogus"
    api = "https://mmc.wd1.myworkdayjobs.com/wday/cxs/mmc/MMC/jobs"

    class Rejected(Exception):
        response = FakeResponse({}, status=400)

    def handler(kw):
        if kw["json"]["appliedFacets"]:
            r = FakeResponse({}, status=400)
            r.raise_for_status = lambda: (_ for _ in ()).throw(Rejected())
            return r
        return FakeResponse({"total": 1, "jobPostings": [{"title": "Analyst", "externalPath": "/job/x", "bulletFields": ["R9"]}]})

    s = FakeSession({api: handler})
    jobs = workday.fetch({"name": "MMC", "url": url}, s)
    assert [j.job_id for j in jobs] == ["R9"]
    assert len(s.calls) == 2


def test_workday_multiple_search_terms_are_deduplicated():
    api = "https://mmc.wd1.myworkdayjobs.com/wday/cxs/mmc/MMC/jobs"

    def handler(kw):
        term = kw["json"]["searchText"]
        ids = {"analyst": ["R1", "R2"], "associate": ["R2", "R3"]}[term]
        return FakeResponse({"total": len(ids), "jobPostings": [
            {"title": t, "externalPath": f"/job/{t}", "bulletFields": [t]} for t in ids]})

    s = FakeSession({api: handler})
    jobs = workday.fetch({"name": "MMC", "url": "https://mmc.wd1.myworkdayjobs.com/MMC", "search": ["analyst", "associate"]}, s)
    assert sorted(j.job_id for j in jobs) == ["R1", "R2", "R3"]


def test_slash_titles_keep_the_junior_level():
    from job_watcher.models import Job
    rules = {"include_keywords": ["analyst", "associate", "consultant"], "exclude_keywords": ["senior", "manager"]}
    t = lambda title: matches(Job("C", title, title, "", "u"), rules)
    assert t("Analyst/Senior Analyst (TMT)")
    assert t("Kearney Foresight Senior Business Analyst / Associate")
    assert not t("Senior Analyst / Manager")
    assert not t("Senior Associate, Working Capital")
