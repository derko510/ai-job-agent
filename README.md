# Job hunt template (Claude Code)

An automated job hunt that runs inside Claude Code:

- **Finds jobs every morning**: ~2,200 company job boards (Greenhouse, Ashby, Lever) plus the SimplifyJobs New-Grad list.
- **Ranks them your way**: jobs near home first (software roles on top), then remote, then jobs elsewhere only if the pay
  clears the bar you set for relocating. Highest pay first inside each group.
- **Applies for you**: one tailored 1-page resume per job, every form answer taken only from your profile. A cheap model
  (Haiku) fills the form; a stronger one (Sonnet) double-checks every application before it is submitted.
- **Watches your Gmail** every 6 hours (read-only): rejections, coding tests with deadlines, recruiter calls (with prep notes).
- **Telegram reminders** (optional) a day before and an hour before each interview, and before coding-test deadlines.
- **Live dashboard** on claude.ai with your pipeline, calls, tests, every application and the exact resume sent.

It never sends emails or messages, never creates accounts or types passwords, never solves CAPTCHAs, and only ever
submits job applications. See SAFETY.md.

## Start

1. Put this folder anywhere (e.g. `~/job-hunt`) and open Claude Code in it: `cd ~/job-hunt && claude`
2. Say: **"set up my job hunt"** - Claude asks for your resume and walks you through a short interview, builds your
   profile, base resume and dashboard, picks your Chrome browser, and turns on the daily schedule.
3. After that, just say **"start hunting"** whenever you open Claude Code here.

You need: Python 3.9+, LaTeX (`pdflatex`), the Claude in Chrome extension, and (recommended) the Gmail connector.

## Files

| File | What it is |
|---|---|
| `profile.json` | your facts and preferences (created by setup; never shared; see `profile.example.json`) |
| `resumes/_base/resume_base.tex` | your base resume (created by setup) |
| `applications.json`, `calls.json`, `oas.json` | the tracker (start empty) |
| `.claude/skills/job-hunt/SKILL.md` | everything Claude does: setup and daily operation |
| `routines/` | the scheduled jobs: daily scan, daily apply, email check, dashboard refresh |
| `workflows/rolling-apply.js` | the apply workflow (Haiku prep -> Sonnet verify -> Haiku submit) |

## Notes

- Schedules run inside an open Claude Code session and expire after 7 days; reopen and say "start hunting" to restart.
- Applying costs about 2-3 agent runs per job. Use the location and level settings to keep the queue relevant.
- Greenhouse often sends an email code before submitting; those jobs are skipped (max 5 Greenhouse tries a day).
  Lever shows a CAPTCHA on submit, so Lever is skipped by default.
- `.gitignore` keeps all personal files out of git if you version this folder.
