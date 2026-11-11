"""Daily job scan, plain Python, no AI.

Re-crawls ~2,200 company job boards plus the SimplifyJobs New-Grad list, applies the profile's filters (location rule,
per-company cap, free pre-screen for too many years / clearance / PhD), ranks the result (rank_queue.py) and writes
candidates_next.json (the next apply run's queue; candidates.json is left alone so a running batch isn't disturbed).
Logs the result and, if Telegram is set up, sends one short summary. Run: python -I job_scan.py
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from activity_log import log_event
import notify


def main():
    cur = os.path.join(HERE, 'candidates.json'); nxt = os.path.join(HERE, 'candidates_next.json')
    saved = open(cur, 'rb').read() if os.path.exists(cur) else None
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'build_queue.py')], cwd=HERE,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        log_event('error', 'daily job scan failed', tail=(r.stderr or r.stdout)[-400:])
        notify.send('⚠️ Daily job scan failed. Claude will look at it next run.')
        return
    c = json.load(open(cur, encoding='utf-8'))
    if saved is not None:
        open(cur, 'wb').write(saved)
    try:  # SimplifyJobs New-Grad list: apply-ready postings go to the front before ranking
        from simplify_scan import scan as simplify
        ready, account = simplify()
    except Exception as e:
        ready, account = [], []
        log_event('error', f'SimplifyJobs scan failed: {type(e).__name__}')
    have = {x.get('url') for x in c}
    c = [x for x in ready if x['url'] not in have] + c
    from rank_queue import rank, TIERS
    c = rank(c)
    json.dump(c, open(nxt, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    json.dump(account, open(os.path.join(HERE, 'simplify_needs_signin.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    from collections import Counter
    t = Counter(x['tier'] for x in c)
    summary = ', '.join(f'{TIERS[k]} {t[k]}' for k in sorted(t))
    log_event('scan', f'daily scan: {len(c)} matching jobs queued ({summary}); SimplifyJobs needing a company sign-in: {len(account)}')
    notify.send(f'🔎 Daily scan: {len(c)} jobs ready to apply to\n({summary})')


if __name__ == '__main__':
    main()
