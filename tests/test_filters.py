from job_watcher.filters import matches, rules_for
from job_watcher.models import Job

RULES = {
    "include_keywords": ["analyst", "associate", "business operations"],
    "exclude_keywords": ["senior", "sr", "manager"],
    "locations": ["mumbai", "india", "remote"],
}


def job(title, location="Mumbai"):
    return Job(company="C", job_id=title, title=title, location=location, url="u")


def test_include_and_exclude():
    assert matches(job("Business Analyst"), RULES)
    assert not matches(job("Senior Business Analyst"), RULES)
    assert not matches(job("Sr. Analyst"), RULES)
    assert not matches(job("Software Engineer"), RULES)


def test_whole_word_matching():
    # "associate" must not match inside "associated"; "manager" exclusion must not hit "management"
    assert not matches(job("Associated Press Writer"), RULES)
    assert matches(job("Associate, Management Consulting"), RULES)


def test_phrase_matching():
    assert matches(job("Business Operations Intern"), RULES)
    assert not matches(job("Operations Business Partner"), RULES)


def test_location_filter():
    assert not matches(job("Analyst", "New York"), RULES)
    assert matches(job("Analyst", "Remote - APAC"), RULES)
    assert matches(job("Analyst", ""), RULES)  # unknown location is kept, not dropped


def test_empty_rules_match_everything():
    assert matches(job("Anything", "Anywhere"), {})


def test_company_override():
    merged = rules_for({"filters": {"locations": ["london"]}}, RULES)
    assert merged["locations"] == ["london"]
    assert merged["include_keywords"] == RULES["include_keywords"]
