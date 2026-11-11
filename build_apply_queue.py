"""Build today's apply list for the rolling-apply workflow from candidates_next.json (already ranked by rank_queue.py).

Drops: anything already in applications.json (by link or posting id), Lever (hCaptcha on submit, if limits.skip_lever),
companies at the per-company cap, excluded companies, and Greenhouse jobs beyond today's limit. Keeps the ranked order.
Writes apply_queue_today.json and prints the Workflow args as JSON (including the FACTS text, root folder and browser).
Usage: python -I build_apply_queue.py [max_jobs]
"""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from capfilter_keys import keys
from jobprofile import load, excluded, facts, check
P = load()
missing = check(P)
if missing:
    raise SystemExit('setup is not finished, missing: ' + ', '.join(missing))
CAP = int(P['limits'].get('max_per_company', 3))
GH_PER_DAY = int(P['limits'].get('greenhouse_per_day', 5))
POST_ID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|/jobs/(\d{6,})')
norm = lambda u: re.sub(r'[?#].*$', '', u or '').rstrip('/').replace('/application', '').replace('/apply', '')
pid = lambda u: (lambda m: m and (m.group(1) or m.group(0)))(POST_ID.search(u or ''))

today = datetime.date.today().isoformat()
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**6
apps = json.load(open(os.path.join(HERE, 'applications.json'), encoding='utf-8'))
seen = {norm(a.get('link')) for a in apps} | {pid(a.get('link')) for a in apps}
cnt = {}
for a in apps:
    if a['status'] != 'Skipped':
        for k in keys(a['company'], a.get('link')):
            cnt[k] = cnt.get(k, 0) + 1
gh_left = GH_PER_DAY - sum(1 for a in apps if a.get('applied') == today and a['status'] != 'Skipped' and 'greenhouse' in (str(a.get('portal')) + str(a.get('link'))).lower())

out = []
for x in json.load(open(os.path.join(HERE, 'candidates_next.json'), encoding='utf-8')):
    if len(out) >= limit:
        break
    url = x.get('apply_url') or x.get('url')
    portal = (x.get('portal') or '').lower()
    co = x.get('company') or ''
    if P['limits'].get('skip_lever', True) and ('lever' in portal or 'lever.co' in (url or '')):
        continue
    if norm(url) in seen or norm(x.get('url')) in seen or (pid(url) and pid(url) in seen):
        continue
    if excluded(co, P):
        continue
    ks = keys(co, url)
    if max(cnt.get(k, 0) for k in ks) >= CAP:
        continue
    if 'greenhouse' in portal or 'greenhouse.io' in (url or ''):
        if gh_left <= 0:
            continue
        gh_left -= 1
    for k in ks:
        cnt[k] = cnt.get(k, 0) + 1
    out.append({'company': co, 'title': x.get('title'), 'location': x.get('location'), 'portal': portal or 'other', 'apply_url': url})

path = os.path.join(HERE, 'apply_queue_today.json')
json.dump(out, open(path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
gh = sum(1 for o in out if 'greenhouse' in o['portal'])
print(json.dumps({'queue': path, 'root': HERE, 'today': today, 'name': P.get('name', ''), 'email': P.get('email', ''),
                  'browser': P.get('browser_device_id', ''), 'cap': CAP, 'facts': facts(P),
                  'target': len(out), 'batch': 15, 'total': len(out), 'ghMax': gh}))
