"""Rebuild the apply queue: crawl the job boards, merge, location rule, per-company cap, free pre-screen.
Ranking (home area first, then remote, then high-pay relocation) happens in rank_queue.py, called by job_scan.py.
Run: python -I build_queue.py"""
import json, os, re, subprocess, sys
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from locations import location_ok, NON_US
from jobprofile import load
P = load()
run = lambda *a: subprocess.run([sys.executable, '-I', *a], cwd=HERE, check=True)

run('crawl_boards.py')
m = json.load(open(os.path.join(HERE, 'candidates.json'), encoding='utf-8'))
if P['targets'].get('also_systems_roles'):
    run('crawl_boards.py', '--systems')
    seen = {x['url'] for x in m}
    m += [x for x in json.load(open(os.path.join(HERE, 'candidates_systems.json'), encoding='utf-8')) if x['url'] not in seen]

m = [x for x in m if location_ok(x.get('location', ''))]
if P['limits'].get('skip_lever', True):
    m = [x for x in m if x.get('portal') != 'lever']  # Lever shows an hCaptcha on submit, which the agents never solve


def remote(x):
    l = x.get('location', '') or ''
    return bool(re.search(r'remote|anywhere|distributed', l, re.I)) and not re.search(r'hybrid', l, re.I) and not NON_US.search(l)


NOW = datetime.now(timezone.utc).timestamp()


def posted(x):
    u = str(x.get('updated') or '')
    try:
        return int(u) / 1000 if u.isdigit() else datetime.fromisoformat(u.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0


for x in m:
    x['remote'] = remote(x)
    x['fresh'] = bool(posted(x)) and NOW - posted(x) <= 3 * 86400  # cold applications do best in the first 1-3 days
m.sort(key=lambda x: (not x['fresh'], -posted(x)))
json.dump(m, open(os.path.join(HERE, 'candidates.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
run('capfilter.py', HERE)
run('prefilter.py')
