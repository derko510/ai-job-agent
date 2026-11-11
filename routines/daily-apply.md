# Daily rolling apply (every morning, after the scan)

1. In this job-hunt folder run `python3 -I build_apply_queue.py` and read the JSON it prints (the Workflow args).
   It builds today's ranked apply list from candidates_next.json: skips jobs already handled, Lever (CAPTCHA), capped and
   excluded companies, and Greenhouse beyond the daily limit. If it says setup is not finished, stop and tell the candidate.
2. If "total" is 0, reply "nothing new to apply to today" and stop.
3. Otherwise start the rolling apply with the Workflow tool: scriptPath = `<this folder>/workflows/rolling-apply.js`,
   args = exactly the printed JSON. It runs in the background:
   - Haiku agents prepare each job (job description, real form questions, eligibility, tailored resume, drafted answers),
   - a Sonnet agent independently re-checks each one (eligibility, resume truthfulness, every answer),
   - Haiku submits verified jobs one at a time in the chosen Chrome (Sonnet retries a failed submit once),
   - every result is written to applications.json and the activity log as it happens.
   Reply with one line saying how many jobs it is applying to.
4. When it finishes: report submissions, skips that need the candidate (CAPTCHAs on forms they can finish by hand,
   questions only they can answer), and run the dashboard refresh (routines/dashboard-refresh.md).

The daily cost is roughly 2-3 agent runs per job (mostly Haiku, one Sonnet check each).
