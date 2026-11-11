"""Free (no-AI) pre-screen of candidates.json before the apply workflow spends tokens on them.

Fetches each posting's description (same APIs as fetch_jds.py) and drops hard blockers:
PhD-only, active security clearance required, more years than profile max_years_required, senior/staff/lead/manager titles,
non-US-only roles. Also tags fully remote US roles and keeps them at the front of the queue.
Usage: python -I prefilter.py [--limit N]   (rewrites candidates.json in place; drops are logged to prefilter_dropped.json)
"""
import json, os, re, sys, concurrent.futures as cf
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch_jds import fetch
from jobprofile import load, home_regex
P = load()
# 'N+ years required' blocks when N is above the profile's max_years_required
TOO_MANY = '|'.join(str(n) for n in range(int(P['targets'].get('max_years_required', 5)) + 1, 20))

BLOCK = [
    ('phd only', re.compile(r'(phd|ph\.d\.?)\s+(is\s+)?required|must (have|hold) a (phd|ph\.d)|currently (enrolled|pursuing) (in )?a (phd|ph\.d)', re.I)),
    ('clearance', re.compile(r'(active|current)\s+(ts/sci|top secret|secret|dod)[^.\n]{0,40}clearance[^.\n]{0,40}(required|is required|must)|must (have|hold|possess) an? (active|current) [^.\n]{0,30}clearance', re.I)),
    ('years', re.compile(r'\b(' + TOO_MANY + r')\s*\+?\s*(or more\s+)?years?\s+(of\s+)?(professional\s+|industry\s+|relevant\s+|hands-on\s+|production\s+)?(software|engineering|work|experience|development|programming)', re.I)),
]
TITLE_BAD = re.compile(r'\b(senior|sr\.?|staff|principal|lead|manager|director|head of|architect)\b', re.I)
REMOTE = re.compile(r'\b(fully remote|100% remote|remote[- ]first|work from anywhere|remote \(us|remote - us|remote, us|remote within the (us|united states)|this (role|position) is remote|remote position)', re.I)
ONSITE = re.compile(r'\b(hybrid|on-?site|in[- ]office|in the office)\b[^.\n]{0,40}\b(days?|required|expected|week)', re.I)

def check(c):
    if TITLE_BAD.search(c.get('title', '')):
        return c, 'title', ''
    try:
        jd, _ = fetch(c.get('url') or c.get('apply_url'), c.get('company', ''))
    except Exception:
        jd = ''
    for name, rx in BLOCK:
        m = rx.search(jd or '')
        if m and not re.search(r'prefer|nice to have|bonus|plus|not required', jd[m.start():m.end() + 60], re.I):
            return c, name, m.group(0)[:120]
    c['remote'] = bool(c.get('remote')) or bool(REMOTE.search(jd or '') and not ONSITE.search(jd or ''))
    return c, '', ''

def main():
    cands = json.load(open(os.path.join(HERE, 'candidates.json'), encoding='utf-8'))
    lim = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else len(cands)
    work, rest = cands[:lim], cands[lim:]
    keep, drop = [], []
    with cf.ThreadPoolExecutor(16) as ex:
        for c, why, ev in ex.map(check, work):
            (drop if why else keep).append(c if not why else dict(company=c['company'], title=c['title'], url=c.get('url'), why=why, evidence=ev))
    bay = home_regex(P)
    keep.sort(key=lambda c: (not c.get('fresh'), not (c.get('remote') or bay.search(c.get('location') or ''))))
    json.dump(keep + rest, open(os.path.join(HERE, 'candidates.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    json.dump(drop, open(os.path.join(HERE, 'prefilter_dropped.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    from collections import Counter
    print('checked', len(work), 'kept', len(keep), 'remote', sum(1 for c in keep if c.get('remote')), 'dropped', dict(Counter(d['why'] for d in drop)))

if __name__ == '__main__':
    main()
