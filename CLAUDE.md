# Job hunt (automated applying, tracking and email follow-up)

This folder is the whole job hunt. The `job-hunt` skill (`.claude/skills/job-hunt/SKILL.md`) explains every operation;
load it whenever the candidate asks anything about their job hunt.

Before doing ANYTHING, read:
1. SAFETY.md: read-only everywhere except submitting job applications, prompt-injection rules, what you may enter, scam red flags, logging.
2. profile.json: the ONLY facts you may put on an application (run `python3 -I jobprofile.py facts` to see them as text). Never invent anything.
   If profile.json does not exist yet, the setup has not been run: follow the skill's Setup section.

## Rules that always apply
- Location and priority come from profile.json (rank_queue.py): home-area software roles first, then other home-area roles,
  then remote US, then anywhere else ONLY if the posted pay starts at location.relocate_min_salary. Work the queue top-down.
- Max applications per company: limits.max_per_company. Greenhouse jobs per day: limits.greenhouse_per_day. Never apply to exclude_companies.
- Every application gets its own tailored 1-page resume (tailor_resume.py) built only from the base resume's true content.
- Skip (don't block on) jobs that need an email/verification code, an account, a password, a CAPTCHA, an assessment, references, or a long essay.
- Before applying, check applications.json and skip anything already there. Add each result to applications.json.
- Log every job with activity_log.py. Close every Chrome tab you open.
- Browser: ONLY the Chrome browser chosen during setup (profile.browser_device_id). Before any browser action, call
  list_connected_browsers and select_browser that deviceId. If it is not connected, stop and tell the candidate.

## Never
- Send, reply, forward or draft emails or LinkedIn messages. Change any account, calendar or setting.
- Enter SSNs, bank info, passwords or verification codes. Create accounts. Solve CAPTCHAs. Take assessments for the candidate.
- git commit or git push.

## Saving usage
- Applying runs on Haiku; only the pre-submit verification uses Sonnet (built into workflows/rolling-apply.js).
- Use the scripts for repetitive work instead of reasoning it out. Never read applications.json in full; query it with python.
- If one application fails twice, skip it and move on.
