# Handoff: add Job Watcher to shubhamtanna.in
8 Nov 2026 · For the website chat (Claude working in `ShubhamTanna/shubhamtanna-site`). The project is built and live; this doc is everything needed to put it on the site.

## Objective
Add Job Watcher to the Work page as a project with its own page, and move it out of the About page's "Now → building" list where it currently sits at `stage: Building`. Follow EDITING.md exactly: every number from `portfolio/facts.md`, charts from `portfolio/chart-*.csv`, gallery from `portfolio/screens.csv`.

## Current state
- **Live** on GitHub Actions since 8 Nov 2026, running daily at 08:47 IST. Repo: https://github.com/ShubhamTanna/job-watcher (public).
- At launch: 2 manual runs, both successful. The first scheduled run was due 8 Nov 08:47 IST.
- `portfolio/` is complete: `facts.md`, `chart-1.csv`, `chart-2.csv`, `screens.csv`, `screens/01-alert.png`, `screens/02-run-log.png`.
- Shubham is moving the project folder from `~/Desktop/Projects/job-watcher` into the portfolio site's projects folder on his desktop. **That folder is not a git clone.** It's a synced copy that matches GitHub except `.github/workflows/daily.yml`, which is older locally (that doesn't affect the site). If the copies ever disagree, the GitHub repo wins, and `data/` there grows every day.
- The site does not have a `content/projects/job-watcher.yaml` yet.

## Decisions (and why)
- **Origin `personal`, team Solo, section Build.** It's a personal tool, the same kind of project as Research Buddy.
- **Charts use launch-day numbers only (8 Nov 2026).** `data/` keeps growing daily. A frozen snapshot keeps every number on the site traceable to facts.md.
- **Gallery images are rendered from real output, not GitHub screenshots.** GitHub's page styling couldn't load from the build environment. `01-alert.png` is issue #2's real content word for word; `02-run-log.png` is run 42419819384's real log lines. Shubham can swap in real GitHub screenshots later if he wants.
- **Unwatchable firms are shown, not hidden.** Four target firms (McKinsey, Bain, A&M, Grant Thornton Bharat) block automated access, and the project deliberately didn't bypass them. That's a judgement point worth showing, so it belongs on the page.

## Not decided yet: confirm with Shubham before publishing
1. **Tier and rank.** Recommended: Tier 2, next to Research Buddy (rank 11). It's a utility, not an analysis, so it doesn't displace the Tier 1 work. Shubham hasn't confirmed this.
2. **Finished vs. his own done-when.** The site's Now entry says: `doneWhen: It runs reliably on GitHub Actions for 2 weeks.` At launch it had 2 runs. Shubham wants it shown as finished. Recommended way to do both honestly:
   - Add the Work page entry now.
   - Set its Now entry to `stage: Live` (one of the four allowed words).
   - Add a log line.
   - Remove it from `building:` after 22 Nov 2026, once the run record is in facts.md.
   - Make no reliability claim ("runs reliably", "for weeks") until then.
3. **Repo visibility.** The `code:` button needs the repo to stay public. Shubham was told that public exposes his target-firm list and the daily alert issues, and he hasn't decided. If he makes it private, remove `code:`.

## Draft project YAML (`content/projects/job-watcher.yaml`)
Every number below is in facts.md. Rewrite the wording freely in Shubham's voice (first person, short sentences, no banned words), but don't change the numbers.

```yaml
# Tier 2: short page.
# Private notes go in content/private/internal-notes.yaml (gitignored), never here.

slug: job-watcher
rank: 12            # confirm (see "Not decided yet")
tier: 2             # confirm
type: build
origin: personal
section: Build
title: Job Watcher
cardTitle: Job Watcher
cardLine: A daily automation that checks 7 consulting and advisory firms' career portals, keeps junior roles in India and alerts me only to new ones.
hero:
  value: 7 firms
  label: checked every morning, ₹0 to run
year: "2026"
team: Solo
tools:
  - Python
  - GitHub Actions
  - REST APIs
problem: Consulting firms post roles on 6 different career-portal systems, and checking each one by hand every day doesn't happen.
did:
  - Wrote a reader for each portal system (Workday, Phenom, iCIMS Jibe, Yello, Oleeo, SuccessFactors) that turns every listing into the same record.
  - Filtered by role, seniority and location, then compared against everything seen before, so alerts only show new postings.
  - Put it on GitHub Actions to run daily at 08:47 IST for ₹0. Each day with new matches opens a GitHub issue that emails me.
  - Left alone the 4 firms that block automated access, and used their own job alerts instead.
results:
  - caption: Coverage at launch
    columns:
      - Firm
      - Status
    rows:
      - - ZS, Kearney, L.E.K., BearingPoint, FTI, Marsh McLennan (incl. Oliver Wyman), BCG
        - Watched daily
      - - McKinsey, Bain, Alvarez & Marsal, Grant Thornton Bharat
        - Not watched. Their systems block automated access, so I use each firm's own alert
    source: config.yaml
story:
  title: The filter that let 62 jobs through
  text: "On the first live run, Marsh McLennan's portal rejected the India filter I had copied from FTI's. The script fell back to every location, and 62 roles from places like Florida, Munich and Sydney reached my alert. The fix: look up each portal's own filter instead of reusing one. The rerun returned 69 India postings and 7 real matches."
skills:
  - Automation
  - APIs
  - Data pipelines
  - Testing
links: []
charts:
  - kind: bar
    file: chart-1.csv
    title: 666 postings in, 39 worth reading
    label: stage
    value: postings
    note: Launch run, 8 Nov 2026. Postings with no location are kept on purpose rather than dropped.
  - kind: bar
    file: chart-2.csv
    title: Where the matches came from
    label: firm
    value: matches
    detail: "{postings_scanned} postings · {portal_system}"
    note: Launch run, 8 Nov 2026. Kearney listed 173 roles, none in India.
code: https://github.com/ShubhamTanna/job-watcher
```

Check before committing:
- That a Tier 2 page renders `results`, `story` and `charts`. Research Buddy's Tier 2 file leaves them empty, so confirm the template supports them, or move the content into `did`.
- That `detail:` with two placeholders works. Player Detection only uses one.

## About page changes (`content/about.yaml`)
- Under `now.building`, entry `name: Job-portal watcher`: change `stage: Building` to `stage: Live`. Optionally update `line:` to "Checks 7 consulting and advisory firms' portals every morning and alerts me to new junior roles in India." Keep `doneWhen:` until 22 Nov.
- Add a line at the **top** of `now.log`: `- date: Nov 2026` / `text: Launched Job Watcher: daily alerts for new roles at 7 consulting and advisory firms.`

## Import
Per EDITING.md section 7, from a folder with the site and the project side by side. The exact single-project form is unconfirmed, so check the import script:
```bash
cd shubhamtanna-site
npm run import -- ../job-watcher job-watcher
```
The import copies `chart-1.csv`, `chart-2.csv`, `facts.md` and the screens. Check that the column names match the chart specs above.

## Verbatim essentials
- Name: **Job Watcher**. Repo: `ShubhamTanna/job-watcher`. Schedule: **08:47 IST daily**.
- Launch funnel: **666** scanned → **257** in target locations → **39** matched.
- Matches by firm: ZS 18 · Marsh McLennan 7 · BCG 6 · L.E.K. 5 · BearingPoint 2 · FTI 1 · Kearney 0.
- **5 of the 7** Marsh McLennan matches are Oliver Wyman roles.
- **38** tests. **1,106** lines of Python. **31–37 s** per run. **₹0** to run.
- Write "Marsh McLennan", not "Marsh", where the Oliver Wyman roles are meant. Kearney's portal is Yello; BearingPoint's is its own page backed by SuccessFactors.

## Working preferences (from Shubham)
- Direct and blunt, no filler. Push back when something's wrong.
- No number on the site unless it's in facts.md. Don't present personal or coursework projects as client work or impact.
- Hyperlinks to outside sites, including the repo, open in a new tab.
- He reworks drafted copy in his own words later, so keep drafts plain and factual.

## Open items
- **Next step:** create `content/projects/job-watcher.yaml` from the draft, run the import, update `about.yaml`, and preview at phone and desktop sizes. Confirm tier and rank with Shubham first.
- **Then:** after 22 Nov 2026, add the 2-week run record to `portfolio/facts.md` in the job-watcher repo, re-import, and remove the entry from Now → building.
- **Pending on Shubham's side, not the site's:** whether to keep the repo public, and whether to drop the broad `operations` keyword from `config.yaml`. It lets through roles like "Office Operations Coordinator".

## Suggested opening prompt
> In shubhamtanna-site, add my Job Watcher project. The handoff is at `job-watcher/portfolio/HANDOFF.md` in my projects folder (repo: github.com/ShubhamTanna/job-watcher). Read it and the project's `portfolio/facts.md` first. I'm confirming it as Tier 2, rank [__]. Create the project YAML from the draft, run the import, update the Now section as described, preview it, and push.
