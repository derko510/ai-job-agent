"""Per-company cap on candidates.json: keep at most limits.max_per_company applications per company (any status except
Skipped counts), and drop excluded companies. Usage: python -I capfilter.py <job-hunt folder>"""
import json, os, sys
from collections import Counter
J = sys.argv[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capfilter_keys import keys, norm
from jobprofile import load, excluded
P = load()
CAP = int(P['limits'].get('max_per_company', 3))
apps = json.load(open(J + '/applications.json', encoding='utf-8'))
cnt = Counter(k for a in apps if a['status'] != 'Skipped' for k in keys(a['company'], a.get('link')))
c = json.load(open(J + '/candidates.json', encoding='utf-8'))
out = []
for r in c:
    if excluded(r['company'], P):
        continue
    ks = keys(r['company'], r.get('url') or r.get('apply_url'))
    if max(cnt[k] for k in ks) < CAP:
        for k in ks: cnt[k] += 1
        out.append(r)
json.dump(out, open(J + '/candidates.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(c), '->', len(out), 'companies', len({norm(r['company']) for r in out}))
