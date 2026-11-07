# Facts: Job Watcher

Snapshot as of launch, 8 Nov 2026 (IST). Dates inside `data/` and the alert titles are in UTC, so launch-day records show 2026-11-07.

## What it is

| Fact | Value | Source |
|---|---|---|
| What | Daily automation that checks target firms' career portals, filters for junior roles in India and alerts on new postings only | README |
| Origin | Personal project, solo | — |
| Built | 19 Oct – 8 Nov 2026 (first version 19 Oct, live on GitHub Actions 8 Nov) | original file dates; git history starts 8 Nov |
| Runs on | GitHub Actions, daily at 08:47 IST (cron `17 3 * * *` UTC) | `.github/workflows/daily.yml` |
| Cost to run | ₹0 (GitHub Actions is free for public repos) | — |
| Run time | 31–37 seconds per run, including setup | GitHub Actions runs 42419636140 and 42419819384 |
| Alerts | A GitHub issue for each day with new matches, which GitHub emails and pushes to the GitHub app; Telegram and email optional | `job_watcher/notify.py` |
| Code | 1,106 lines of Python (+ 549 lines of tests) | `job_watcher/`, `tests/` |
| Tests | 38 automated tests, run on every push in GitHub CI | `tests/`, `.github/workflows/tests.yml` |

## Coverage

| Fact | Value | Source |
|---|---|---|
| Firms watched daily | 7: ZS, Kearney, L.E.K. Consulting, BearingPoint, FTI Consulting, Marsh McLennan (includes Oliver Wyman and Mercer roles), BCG | `config.yaml` |
| Different portal systems read | 6: iCIMS Jibe, Yello, Oleeo, SuccessFactors (BearingPoint's own page), Workday, Phenom | `job_watcher/sources/` |
| Portal adapters written | 10 (the 6 above plus Greenhouse, Lever, Ashby and Talemetry) | `job_watcher/sources/__init__.py` |
| Firms on the target list not watched | 4: McKinsey, Bain, Alvarez & Marsal, Grant Thornton Bharat | `config.yaml` |
| Why not | McKinsey: job API behind bot protection, page shows only the first 20 roles. Bain: API answers "Forbidden: Direct API access is not allowed". A&M: returns 403 to GitHub Actions servers. Grant Thornton Bharat: private, token-authenticated, encrypted API. Each one uses the firm's own job alert instead; no protection was bypassed | `config.yaml`, run logs |

## Launch results (8 Nov 2026)

| Fact | Value | Source |
|---|---|---|
| Postings scanned | 666 | `data/history.csv` |
| In target locations | 257 (location matches an Indian city, "India" or "Remote", or no location given; blank locations are kept on purpose) | `data/history.csv` + `config.yaml` filters |
| Matched role filters | 39 | `data/history.csv`, column `matched` |
| Matches by firm | ZS 18 · Marsh McLennan 7 · BCG 6 · L.E.K. 5 · BearingPoint 2 · FTI 1 · Kearney 0 (of 173 postings, none in India) | `data/history.csv` |
| Oliver Wyman roles found | 5 of the 7 Marsh McLennan matches | `data/history.csv` |
| Two-level titles kept | 5 of the 39 matches are titles like "Analyst/Senior Analyst" that a plain "exclude senior" rule would have dropped | `data/history.csv`, `job_watcher/filters.py` |

## Problems found by the live runs and fixed

| Fact | Value | Source |
|---|---|---|
| Wrong filter id | Marsh McLennan's Workday rejected the India filter id copied from FTI's (HTTP 400), so 62 non-India roles (e.g. Clearwater, Florida; Munich; Sydney) leaked into the first alert | Run 42419636140, issue #1 |
| Fix | The adapter now looks up each Workday tenant's own India filter; the rerun returned 69 India postings and 7 matches | Commit 378a825, run 42419819384, issue #2 |
| Blocked portal | Alvarez & Marsal returned 403 to GitHub's servers on both runs, so it was switched off rather than disguising the script | Commit 80e8840 |

## Not claimed

- No reliability track record yet. The site's own done-when line is "runs reliably on GitHub Actions for 2 weeks"; at launch it had 2 manual runs and the first scheduled run was due 8 Nov 08:47 IST. Add the run count here after 22 Nov 2026.
- No interviews, applications or offers are attributed to this tool.
- Charts use launch-day numbers only; the live `data/` folder keeps growing every day.
