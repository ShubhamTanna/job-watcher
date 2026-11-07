"""End-to-end runs against fake portals: baseline, diff, failure handling."""

import csv
import json

import yaml
from conftest import FakeResponse, FakeSession, load

from job_watcher import main, notify

GH = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
LV = "https://api.lever.co/v0/postings/beta"


def write_config(tmp_path, companies):
    cfg = {
        "filters": {"include_keywords": ["analyst", "associate"], "exclude_keywords": ["senior", "manager"],
                    "locations": ["mumbai", "bengaluru"]},
        "companies": companies,
    }
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return str(p)


COMPANIES = [
    {"name": "Acme", "source": "greenhouse", "board": "acme"},
    {"name": "Beta", "source": "lever", "board": "beta"},
]


def no_alert_channels(monkeypatch):
    for k in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SMTP_USER", "SMTP_PASSWORD", "ALERT_GITHUB_ISSUE"]:
        monkeypatch.delenv(k, raising=False)


def test_github_issue_alert(tmp_path, monkeypatch):
    no_alert_channels(monkeypatch)
    monkeypatch.setenv("ALERT_GITHUB_ISSUE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_x")
    monkeypatch.setenv("GITHUB_REPOSITORY", "ShubhamTanna/job-watcher")
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "ShubhamTanna")
    cfg = write_config(tmp_path, COMPANIES)
    s = FakeSession({GH: load("greenhouse.json"), LV: load("lever.json"), "https://api.github.com/repos/": {}})
    assert main.run(cfg, tmp_path / "data", session=s) == 0
    issue = [c for c in s.calls if c[1].startswith("https://api.github.com")][0]
    assert issue[1] == "https://api.github.com/repos/ShubhamTanna/job-watcher/issues"
    body = issue[2]["json"]
    assert body["title"].startswith("2 new role(s)")
    assert "[Business Analyst](https://boards.greenhouse.io/acme/jobs/101) — Mumbai, India" in body["body"]
    assert "@ShubhamTanna" in body["body"] and body["labels"] == ["new-jobs"]
    assert issue[2]["headers"]["Authorization"] == "Bearer ghs_x"


def test_first_run_then_diff(tmp_path, monkeypatch, capsys):
    no_alert_channels(monkeypatch)
    cfg = write_config(tmp_path, COMPANIES)
    data = tmp_path / "data"
    s = FakeSession({GH: load("greenhouse.json"), LV: load("lever.json")})

    assert main.run(cfg, data, session=s) == 0
    out = capsys.readouterr().out
    # Acme: only "Business Analyst" (senior excluded, London excluded, engineer excluded)
    # Beta: only the Strategy & Ops Analyst (manager excluded)
    assert "2 new matching role(s)" in out
    assert "first run: current openings" in out

    seen = json.loads((data / "seen.json").read_text())
    assert len(seen["jobs"]) == 6  # every listed job recorded, matched or not
    rows = list(csv.DictReader((data / "history.csv").open()))
    assert sum(int(r["matched"]) for r in rows) == 2

    # Second run, one new matching job appears at Acme
    gh = load("greenhouse.json")
    gh["jobs"].append({"id": 105, "title": "Associate, Strategy", "absolute_url": "https://x/105",
                       "location": {"name": "Mumbai"}, "updated_at": "2026-10-19"})
    s2 = FakeSession({GH: gh, LV: load("lever.json")})
    assert main.run(cfg, data, session=s2) == 0
    out = capsys.readouterr().out
    assert "1 new matching role(s)" in out
    assert "Associate, Strategy" in out
    assert "first run" not in out

    # Third run, nothing changed
    assert main.run(cfg, data, session=s2) == 0
    assert "Nothing new today." in capsys.readouterr().out


def test_one_failing_source_does_not_block_others(tmp_path, monkeypatch, capsys):
    no_alert_channels(monkeypatch)
    cfg = write_config(tmp_path, COMPANIES)
    s = FakeSession({GH: load("greenhouse.json")})  # lever route missing -> 404
    assert main.run(cfg, tmp_path / "data", session=s) == 0
    out = capsys.readouterr().out
    assert "Beta: RuntimeError: HTTP 404" in out
    assert "Business Analyst" in out


def test_all_sources_failing_exits_nonzero(tmp_path, monkeypatch):
    no_alert_channels(monkeypatch)
    cfg = write_config(tmp_path, COMPANIES)
    assert main.run(cfg, tmp_path / "data", session=FakeSession({})) == 1


def test_failed_alert_does_not_save_state(tmp_path, monkeypatch):
    no_alert_channels(monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    cfg = write_config(tmp_path, COMPANIES)
    s = FakeSession({GH: load("greenhouse.json"), LV: load("lever.json"),
                     "https://api.telegram.org": lambda kw: FakeResponse({}, status=500)})
    assert main.run(cfg, tmp_path / "data", session=s) == 1
    assert not (tmp_path / "data" / "seen.json").exists()  # jobs will be re-alerted tomorrow


def test_telegram_send_and_chunking(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    s = FakeSession({"https://api.telegram.org": {}})
    lines = ["x" * 1000] * 9  # ~9000 chars -> 3 messages
    assert notify.send_telegram(lines, s) is True
    assert len(s.calls) == 3
    assert s.calls[0][2]["json"]["parse_mode"] == "HTML"


def test_dry_run_saves_nothing(tmp_path, monkeypatch):
    no_alert_channels(monkeypatch)
    cfg = write_config(tmp_path, COMPANIES)
    s = FakeSession({GH: load("greenhouse.json"), LV: load("lever.json")})
    assert main.run(cfg, tmp_path / "data", dry_run=True, session=s) == 0
    assert not (tmp_path / "data" / "seen.json").exists()


def test_html_is_escaped():
    from job_watcher.models import Job
    j = Job(company="A&B", job_id="1", title="Analyst <Ops>", location="Mumbai", url="https://x?a=1&b=2")
    text = "\n".join(notify.build_digest([j], [], []))
    assert "A&amp;B" in text and "&lt;Ops&gt;" in text and "a=1&amp;b=2" in text


def test_secrets_redacted_from_errors():
    assert "abc" not in main._redact("https://api.telegram.org/bot123:abc-DEF/sendMessage failed")
