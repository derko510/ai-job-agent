---
name: job-hunt
description: Automated job hunt - first-time setup interview, then daily job-board scans, ranked tailored-resume applications (Haiku applies, Sonnet verifies), Gmail status checks and a live dashboard. Use when the user says "set up my job hunt", "start hunting", "apply to jobs", "check my email for job updates", "refresh the dashboard", "update my profile", "pause the job hunt", or asks anything about their applications.
---

# Job hunt

Everything lives in this folder (the project root, where CLAUDE.md is; call it ROOT below). Read SAFETY.md and CLAUDE.md
first. All personal facts live in `profile.json`; scripts and agents read it, nothing personal is hard-coded.

| Piece | What it does |
|---|---|
| `job_scan.py` | crawls ~2,200 Greenhouse/Ashby/Lever boards (`boards.txt`) + the SimplifyJobs New-Grad list, filters, ranks -> `candidates_next.json` |
| `rank_queue.py` | home-area software roles > other home-area roles > remote US > elsewhere only at the relocation pay floor; highest pay first |
| `build_apply_queue.py` | today's apply list + the Workflow args (incl. the FACTS text from profile.json) |
| `workflows/rolling-apply.js` | Haiku preps each job (JD, real form, eligibility, tailored resume), Sonnet verifies, Haiku submits in Chrome |
| `tailor_resume.py` | 1-page resume per job from `resumes/_base/resume_base.tex` (reorder/reword true content only) |
| `publish_dashboard.py` | syncs the tracker and says which files to publish to the dashboard |
| `routines/*.md` | the scheduled jobs: daily-scan, daily-apply, email-check, dashboard-refresh |

Decide first: run `python3 -I jobprofile.py check` in ROOT. If profile.json is missing or anything is listed as
missing, do **Setup** (only the missing steps). Otherwise go to **Operating**.

---

## Setup (first run; about 15 minutes of the user's time)

Keep it friendly and short. Ask in small batches; use AskUserQuestion for choices, plain chat for free text.
Never invent an answer: anything the user doesn't give stays blank and the agents will skip questions that need it.

### 1. Prerequisites (check, tell the user what's missing)
- `python3 --version` (3.9+) and `pdflatex --version` (TeX Live: `sudo apt install texlive-latex-extra` / `brew install --cask mactex-no-gui`).
- Claude in Chrome extension installed in the Chrome they want to apply from (claude.ai/chrome).
- Gmail connector connected to the inbox their applications will use (for the email check). Optional but recommended.
- The account can create claude.ai Artifacts (for the dashboard). Optional.

### 2. Resume first
Ask for their current resume (path to a PDF/DOCX/TeX file in this folder, or pasted text). Read it fully. Most profile
answers come from it, so later questions only cover the gaps.

### 3. Interview (fill the gaps; confirm what you extracted)
Copy `profile.example.json` to `profile.json` and fill it. Field by field:
- **Contact**: name, legal name, preferred name, email used for applications, phone, street/city/state/zip, LinkedIn, GitHub, portfolio.
- **Work authorization**: authorized in the US? sponsorship now / later? citizenship (for ITAR/export questions)? clearance?
- **Where**: home city; build `location.home_area_places` as the lowercase names of the cities within commuting distance
  (offer a generated list for their metro and let them edit it; include short forms like "sf", "nyc", "la" carefully).
  Remote US OK? Would they relocate, and if so only above what base salary (`relocate_min_salary`, null = never)? On-site OK?
- **What**: target roles. Leave `targets` lists empty for the default (new-grad / early-career software, ML, data, platform,
  forward-deployed, solutions roles). Otherwise set `title_include` (e.g. ["data analyst","business analyst"]),
  `level_include` (e.g. ["junior","associate","new grad","entry"]), `title_exclude`. Max years a posting may REQUIRE (default 5).
  Also look at IT/sysadmin/infrastructure "systems" roles? (`also_systems_roles`).
- **Pay & timing**: desired base, minimum base, internship hourly (if relevant), current salary policy, preferred and earliest start, notice period.
- **Education / experience / projects / skills**: from the resume; confirm. Experience bullets exactly as on the resume.
- **Years of experience** per tool: total (school + projects + work) and professional; estimate together, they approve.
- **EEO**: gender, race, veteran, disability, pronouns-if-required (default: decline to self-identify for each).
- **Answer bank**: travel, NDA/non-compete, ever terminated, background check, driver's license, languages, SAT/GRE,
  references policy, relatives at company, shifts/on-call, anything else they want answered the same way every time.
- **Writing material**: 3-6 true stories/projects with results, used for "why us / proudest work" answers.
- **Never apply to**: current employer and its subsidiaries, plus any others. "May we contact your current employer?" answer.
- **Limits**: max applications per company (default 3), Greenhouse per day (default 5: Greenhouse often emails a code; those jobs get skipped), skip Lever (default yes: CAPTCHA on submit).
- **Telegram alerts**: want them? (see `.env.telegram.example`; they paste the token themselves; never type it for them).
Show a short summary of profile.json and get a yes before continuing.

### 4. Base resume
Write `resumes/_base/resume_base.tex` in the exact structure of `resumes/_base/resume_base.example.tex` (same preamble and
commands: `\resumeSubheading`, `\resumeItem`, `\resumeProjectHeading`, `\textbf{Label}{: items}` skills lines) with ONLY
their real content. Test: write `specs/_test.json` = `{"company": "Test", "slug": "test"}`, run
`python3 -I tailor_resume.py specs/_test.json`; it must print a 1-page PDF path. Show it to them; fix until they approve;
delete the test folder and spec.

### 5. Standard answers
`python3 -I jobprofile.py answers` (writes answers.json for the dashboard; no address or phone in it).

### 6. Browser
Load the Claude in Chrome tools, call `list_connected_browsers`, ask which one to use (AskUserQuestion, one option per
browser). `select_browser` it and save `browser_device_id` and `browser_name` in profile.json. Only that browser is ever used.

### 7. Dashboard (optional but recommended)
1. Artifact `quickstart` with intent "other"; create from the Dashboard type it names (title "<First name>'s job hunt").
2. For each entry in `dashboard/datasets.json`: upload the file (`Artifact` publish, `url` = dashboard, `asset: true`,
   `file_path` = ROOT/<file>) and note its `/_blob/...` url.
3. One `ArtifactData` batch: `dash/meta` = {title}; each `datasets/<id>` = {title, description, schedule, staleAfterHours,
   fixed?, source: {kind: "file", format: "json", name, url: <blob url>}, updated: {at: now, by: "Claude"}};
   `files/index.html` = {text: contents of dashboard/index.html with `{{TITLE}}` replaced by the title}.
4. Read `data/users/me` doc `check` (as the Dashboard type's instructions say) and fix what it reports.
5. Save `dashboard_url` in profile.json, then `python3 -I publish_dashboard.py` and `python3 -I publish_dashboard.py --done`.
Mention: anyone they share the dashboard link with can see their applications.

### 8. Gmail check
Run one `search_threads` with `newer_than:7d` and confirm the account in the results is the profile email. If it is a
different address, tell them the email check will miss replies until they connect the right inbox.

### 9. First scan and a small first run
`python3 -I job_scan.py` (a few minutes). Report the queue by group. Then offer a 3-job trial:
`python3 -I build_apply_queue.py 3` and start the Workflow with its printed args (see Operating). Report what happened.

### 10. Schedules (keep it running without being asked)
Create these with CronCreate (off-minute times are deliberate). Tell the user: they live only in this Claude session,
expire after 7 days, and run only while the session is idle; to restart, open Claude Code in ROOT and say "start hunting".
- Daily scan: `4 5 * * *`, prompt: "Job hunt: follow ROOT/routines/daily-scan.md."
- Daily apply: `23 6 * * *`, prompt: "Job hunt: follow ROOT/routines/daily-apply.md."
- Email check: `17 0,6,12,18 * * *`, prompt: "Job hunt: follow ROOT/routines/email-check.md."
- Dashboard refresh: `7,37 * * * *`, prompt: "Job hunt: follow ROOT/routines/dashboard-refresh.md. One-line reply."
(Write ROOT as the real absolute path. Skip the dashboard and email jobs if those parts were skipped.)

---

## Operating

- **"start hunting" / "apply to jobs"**: make sure the four schedules exist (CronList; create missing ones, never duplicates),
  then follow `routines/daily-apply.md` now.
- **Starting the apply workflow**: `python3 -I build_apply_queue.py [max_jobs]` prints JSON; call Workflow with
  `scriptPath` = ROOT/workflows/rolling-apply.js and `args` = that JSON exactly. It runs in the background; results land
  in applications.json as they happen. When it finishes, summarize submitted / skipped (with reasons) / needs-the-user.
- **"check my email"**: follow `routines/email-check.md` now.
- **"refresh the dashboard"**: follow `routines/dashboard-refresh.md`.
- **"update my profile" / new preference**: edit profile.json, re-run `python3 -I jobprofile.py answers` if answers changed,
  and re-rank: `python3 -I rank_queue.py candidates_next.json`.
- **"pause"**: CronDelete the job-hunt schedules; say how to resume.
- **What needs them**: after every run, list soonest-first: coding tests with deadlines, calls to book (with links),
  CAPTCHA-blocked forms they can finish by hand, questions only they can answer.

## Cost
The apply workflow uses 2-3 agent runs per job (Haiku prep and submit, one Sonnet verification). Skipped jobs still cost a
prep and a verify, so the location/level filters and the Lever/Greenhouse limits matter. Tell the user roughly how many
jobs a run will cover before the first big run.
