"""Rank the apply queue by the profile's priorities, plain Python, no AI.

Order (pay = midpoint of the posted range): 1) home-area software roles  2) other home-area roles  3) remote (US)
4) elsewhere, only if profile location.relocate_min_salary is set and the posted pay range STARTS at or above it.
Everything else is dropped from the queue. Inside each group: highest posted pay first; no pay listed goes last.

Pay comes from the posting itself (Ashby compensation data, Greenhouse pay ranges, or a $ range in the description).
Adds pay_min / pay_max / tier to each job. Usage: python -I rank_queue.py [candidates_next.json]
"""
import concurrent.futures as cf, html, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from jobprofile import load, home_regex, relocate_min
P = load()
RELOCATE_MIN = relocate_min(P)  # None = never apply outside the home area / remote
HOME = home_regex(P)
SWE = re.compile(r'software|\bswe\b|full[- ]?stack|back[- ]?end|front[- ]?end|developer|forward deployed|machine learning engineer|'
                 r'\bml engineer|\bai engineer|platform engineer|product engineer|infrastructure engineer|mobile|\bios\b|android|'
                 r'founding engineer|applied ai', re.I)
REMOTE = re.compile(r'remote|anywhere|distributed', re.I)
TIERS = ['Home-area software', 'Home-area other', 'Remote', f'Relocate (${RELOCATE_MIN or 0:,}+ floor)', 'Other']


def get(u, t=20):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=t).read().decode('utf-8', 'replace')


def money(s):
    s = s.replace(',', '').strip().lower()
    return float(s[:-1]) * 1000 if s.endswith('k') else float(s)


RANGE = re.compile(r'\$\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s?k)\s*(?:-|–|—|to)\s*\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s?k)', re.I)
HOURLY = re.compile(r'\$\s?(\d{2,3}(?:\.\d+)?)\s*(?:-|–|—|to)\s*\$?\s?(\d{2,3}(?:\.\d+)?)\s*(?:/|per)\s*(?:hr|hour)', re.I)


def pay_from_text(t):
    t = html.unescape(t or '')
    m = RANGE.search(t)
    if m:
        lo, hi = money(m.group(1)), money(m.group(2))
        if 20_000 <= lo <= hi <= 1_000_000:
            return lo, hi
    m = HOURLY.search(t)
    if m:
        return float(m.group(1)) * 2080, float(m.group(2)) * 2080
    return None


_ashby = {}


def ashby_board(org):
    if org not in _ashby:
        try:
            _ashby[org] = {j['id']: j for j in json.loads(get(f'https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true')).get('jobs', [])}
        except Exception:
            _ashby[org] = {}
    return _ashby[org]


def pay_of(x):
    url = x.get('url') or x.get('apply_url') or ''
    try:
        m = re.search(r'jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})', url)
        if m:
            j = ashby_board(m.group(1)).get(m.group(2)) or {}
            for c in ((j.get('compensation') or {}).get('summaryComponents') or []):
                if c.get('compensationType') == 'Salary' and c.get('minValue'):
                    k = 2080 if 'HOUR' in (c.get('interval') or '').upper() else 1
                    return c['minValue'] * k, (c.get('maxValue') or c['minValue']) * k
            return pay_from_text((j.get('compensation') or {}).get('compensationTierSummary')) or pay_from_text(j.get('descriptionPlain'))
        m = re.search(r'greenhouse\.io/(?:embed/job_app\?for=)?([^/?]+)/jobs/(\d+)', url)
        if m:
            j = json.loads(get(f'https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}?pay_transparency=true'))
            for r in j.get('pay_input_ranges') or []:
                if r.get('min_cents'):
                    return r['min_cents'] / 100, (r.get('max_cents') or r['min_cents']) / 100
            return pay_from_text(j.get('content'))
    except Exception:
        pass
    return None


def tier(x):
    loc = x.get('location') or ''
    title = x.get('title') or x.get('role') or ''
    if HOME.search(loc):
        return 0 if SWE.search(title) else 1
    if (x.get('remote') or (REMOTE.search(loc) and not re.search(r'hybrid', loc, re.I))) and P['location'].get('remote_us_ok', True):
        return 2
    return 3 if RELOCATE_MIN and (x.get('pay_min') or 0) >= RELOCATE_MIN else 4


def rank_key(x):
    hi = x.get('pay_max')
    bucket = 0 if hi else 1
    mid = ((x.get('pay_min') or hi or 0) + (hi or 0)) / 2  # midpoint, so very wide ranges don't jump the line
    return (x['tier'], bucket, -mid)


def rank(jobs):
    need = [x for x in jobs if 'pay_max' not in x]
    with cf.ThreadPoolExecutor(16) as ex:
        for x, p in zip(need, ex.map(pay_of, need)):
            x['pay_min'], x['pay_max'] = (int(p[0]), int(p[1])) if p else (None, None)
    for x in jobs:
        x['tier'] = tier(x)
    keep = [x for x in jobs if x['tier'] < 4]  # tier 4 = would need relocating without the pay to justify it
    return sorted(keep, key=rank_key)  # stable: earlier order (freshness) breaks ties


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'candidates_next.json')
    before = json.load(open(path, encoding='utf-8'))
    jobs = rank(before)
    print(len(before) - len(jobs), 'dropped (outside the home area / remote without the relocation pay floor)')
    json.dump(jobs, open(path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    from collections import Counter
    c = Counter(x['tier'] for x in jobs)
    print(len(jobs), 'jobs ranked:', ', '.join(f'{TIERS[t]} {c[t]}' for t in sorted(c)), '| with posted pay:', sum(1 for x in jobs if x.get('pay_max')))
