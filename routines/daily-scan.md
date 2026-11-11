# Daily job scan (every morning)

Bookkeeping only: no AI reasoning needed, no browser, no applying.

1. In this job-hunt folder run with Bash (timeout 600000): `python3 -I job_scan.py`
   It crawls ~2,200 company job boards and the SimplifyJobs New-Grad list, applies the profile's filters, ranks the result
   (rank_queue.py) and writes candidates_next.json. It logs the result and, if Telegram is on, sends one summary.
2. Reply with one line: how many jobs were queued (by group), or the error.
