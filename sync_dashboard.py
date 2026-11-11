"""Merge results from running/finished rolling-apply workflows into applications.json,
rebuild resumes.json and applications_public.json. Prints CHANGED or NOCHANGE.

Workflow run dirs to read are listed in sync_runs.txt (one transcript dir per line).
"""
import json, os, re, sys, ntpath, subprocess
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.join(HERE, 'applications.json')

def rid(c, r):
    return re.sub(r'[^a-z0-9]+', '-', (c + ' ' + r).lower()).strip('-')[:60]
def portal(u):
    return 'Greenhouse' if 'greenhouse' in u else 'Ashby' if 'ashby' in u else 'Lever' if 'lever' in u else 'Other'
def qa(p):
    d = p.get('drafted') or [{'q': f.get('label', ''), 'a': f.get('answer', '')} for f in (p.get('form_fields') or []) if 'drafted' in (f.get('basis') or '') and f.get('answer')]
    return ''.join(f" | Q: {x['q'][:120]} -> A: {x['a'][:600]}" for x in d)
def link(u):
    return re.sub(r'/(application|apply)$', '', u or '')

runs = [l.strip() for l in open(os.path.join(HERE, 'sync_runs.txt'), encoding='utf-8') if l.strip()] if os.path.exists(os.path.join(HERE, 'sync_runs.txt')) else []
apps = json.load(open(APPS, encoding='utf-8'))
have = {a['id'] for a in apps}
added = 0
def add_row(p, r_status, reason, ev):
    global added
    i = rid(p['company'], p['role'])
    if i in have:
        return
    ok = r_status == 'submitted'
    apps.append(dict(id=i, applied=os.environ.get('SYNC_DATE') or __import__('datetime').date.today().isoformat(), company=p['company'], role=p['role'],
                     track='Internship' if re.search(r'intern|co-?op', p['role'], re.I) else 'New grad',
                     location=(p.get('location') or '')[:80], pay=p.get('pay') or 'Not listed', portal=portal(p.get('apply_url', '')),
                     status='Applied' if ok else 'Skipped', link=link(p.get('apply_url')),
                     notes=('Submitted; ' + ('confirmation page shown.' if ('confirmation' in ev or '/thanks' in ev) else 'success message shown.') + ' JD-tailored resume; answers independently verified.' + qa(p)) if ok else (str(r_status) + ': ' + (reason or '')[:220]),
                     resume_file=ntpath.basename(p.get('resume_path') or '') if ok else '', resume_url='',
                     resume_tex=(p.get('resume_path') or '')[:-4] + '.tex' if ok and p.get('resume_path') else ''))
    have.add(i); added += 1

for d in runs:
    if d.endswith('.output') and os.path.exists(d):
        try:
            res = json.load(open(d, encoding='utf-8')).get('result', {}).get('results', [])
        except Exception:
            res = []
        for r in res:
            if r.get('company') and r.get('role') and r.get('status') in ('submitted', 'skipped'):
                add_row(r, r['status'], r.get('reason', ''), r.get('evidence', '') or '')
        continue
    jf = os.path.join(d, 'journal.jsonl')
    if not os.path.exists(jf):
        continue
    labels, results = {}, {}
    for line in open(jf, encoding='utf-8'):
        try:
            j = json.loads(line)
        except Exception:
            continue
        if j.get('type') == 'started':
            labels[j['key']] = j.get('label', '')
        elif j.get('type') == 'result':
            r = j.get('result')
            if isinstance(r, str):
                try: r = json.loads(r)
                except Exception: r = None
            results[j['key']] = r
    prep, ver, appl = {}, {}, []
    for k, r in results.items():
        lab = labels.get(k, '')
        if not isinstance(r, dict):
            continue
        if lab.startswith('prep:'):
            prep[lab[5:]] = r
        elif lab.startswith('verify:'):
            ver[lab[7:]] = r
        elif lab.startswith('apply:') or lab.startswith('apply2:'):
            appl.append((lab.split(':', 1)[1], r))

    def find_prep(key):
        co, _, role = key.partition(':')
        for pk, p in prep.items():
            if (p.get('company') or '')[:28] == co[:28] and (p.get('role') or '')[:20] == role[:20]:
                return pk, p
        return None, None

    applied_keys = set()
    appl.sort(key=lambda kr: kr[1].get('status') != 'submitted')
    for key, r in appl:
        pk, p = find_prep(key)
        if not p:
            continue
        applied_keys.add(pk)
        i = rid(p['company'], p['role'])
        if i in have:
            continue
        ok = r.get('status') == 'submitted'
        ev = r.get('evidence', '') or ''
        apps.append(dict(id=i, applied=os.environ.get('SYNC_DATE') or __import__('datetime').date.today().isoformat(), company=p['company'], role=p['role'],
                         track='Internship' if re.search(r'intern|co-?op', p['role'], re.I) else 'New grad',
                         location=(p.get('location') or '')[:80], pay=p.get('pay') or 'Not listed', portal=portal(p.get('apply_url', '')),
                         status='Applied' if ok else ('Ready' if 'email code' in (r.get('reason') or '') else 'Skipped'), link=link(p.get('apply_url')),
                         notes=('Waiting on email code - enter it in the open Chrome tab.') if 'email code' in (r.get('reason') or '') else ('Submitted; ' + ('confirmation page shown.' if ('confirmation' in ev or '/thanks' in ev) else 'success message shown.') + ' JD-tailored resume; answers independently verified.' + qa(p)) if ok else (str(r.get('status')) + ': ' + (r.get('reason') or '')[:200]),
                         resume_file=ntpath.basename(p.get('resume_path') or '') if ok else '', resume_url='',
                         resume_tex=(p.get('resume_path') or '')[:-4] + '.tex' if ok and p.get('resume_path') else ''))
        have.add(i); added += 1
    for pk, p in prep.items():
        v = ver.get(pk)
        if pk in applied_keys or not v or v.get('ready_to_apply'):
            continue
        i = rid(p['company'], p['role'])
        if i in have:
            continue
        reason = ('Ineligible: ' + (v.get('eligibility_reason') or '')) if v.get('eligible_final') is False else ('Not ready: ' + (v.get('summary') or ''))
        apps.append(dict(id=i, applied=os.environ.get('SYNC_DATE') or __import__('datetime').date.today().isoformat(), company=p['company'], role=p['role'],
                         track='Internship' if re.search(r'intern|co-?op', p['role'], re.I) else 'New grad',
                         location=(p.get('location') or '')[:80], pay=p.get('pay') or 'Not listed', portal=portal(p.get('apply_url', '')),
                         status='Skipped', link=link(p.get('apply_url')), notes=reason[:240], resume_file='', resume_url=''))
        have.add(i); added += 1

if added:
    json.dump(apps, open(APPS, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
subprocess.run([sys.executable, '-I', os.path.join(HERE, 'build_resume_data.py')], check=True)
subprocess.run([sys.executable, '-I', os.path.join(HERE, 'fetch_jds.py')], check=False)
subprocess.run([sys.executable, '-I', os.path.join(HERE, 'notify.py'), '--pending'], check=False)
subprocess.run([sys.executable, '-I', os.path.join(HERE, 'alerts.py')], check=False)
apps = json.load(open(APPS, encoding='utf-8'))
pub = [{k: v for k, v in a.items() if k != 'resume_tex'} for a in apps]
pubf = os.path.join(HERE, 'applications_public.json')
old = open(pubf, encoding='utf-8').read() if os.path.exists(pubf) else ''
new = json.dumps(pub, indent=1, ensure_ascii=False)
open(pubf, 'w', encoding='utf-8').write(new)
# The "applications" stamp moves only when the applications data actually changed.
sys.path.insert(0, HERE)
from stamp_status import stamp, has
if new != old or not has('applications'):
    stamp('applications', applied=sum(a['status'] == 'Applied' for a in apps))
print('CHANGED' if (added or new != old) else 'NOCHANGE', 'added', added, 'total', len(apps), 'applied', sum(a['status'] == 'Applied' for a in apps))
