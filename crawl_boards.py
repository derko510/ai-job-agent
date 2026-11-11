"""Crawl public Greenhouse / Ashby / Lever job boards for US entry-level software roles.

Board tokens come from every link in the SimplifyJobs New-Grad and Internship READMEs (incl. old rows),
plus boards.txt (one 'greenhouse:token' / 'ashby:org' / 'lever:org' per line) if present.
Writes candidates.json: [{company, title, url, apply_url, portal, location, updated, board}]
excluding anything already in applications.json.
"""
import json, re, sys, os, urllib.request, concurrent.futures as cf
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))

def get(u, t=20):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=t).read().decode('utf-8', 'replace')

boards = set()
for repo in ('New-Grad-Positions', 'Summer2027-Internships', 'Summer2026-Internships', 'New-Grad-Positions-2026'):
    try:
        txt = get(f'https://raw.githubusercontent.com/SimplifyJobs/{repo}/dev/README.md', 60)
    except Exception:
        continue
    for m in re.finditer(r'(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_app\?for=)?([A-Za-z0-9_-]+)', txt):
        boards.add(('greenhouse', m.group(1)))
    for m in re.finditer(r'jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)', txt):
        boards.add(('ashby', m.group(1)))
    for m in re.finditer(r'jobs\.lever\.co/([A-Za-z0-9_.-]+)', txt):
        boards.add(('lever', m.group(1)))
extra = os.path.join(HERE, 'boards.txt')
if os.path.exists(extra):
    for line in open(extra, encoding='utf-8'):
        if ':' in line:
            p, t = line.strip().split(':', 1); boards.add((p, t))
boards = {b for b in boards if b[1] not in ('jobs', 'embed')}
print('boards', len(boards), file=sys.stderr)

TITLE_OK = re.compile(r'(software|backend|back-end|full[- ]?stack|frontend|front-end|platform|cloud|devops|site reliability|\bsre\b|infrastructure|machine learning|\bml\b|\bai\b|data engineer|automation|forward deployed|solutions engineer|application(s)? engineer|product engineer|developer)', re.I)
LEVEL_OK = re.compile(r'(intern|co-?op|\bii\b|\b2\b|new grad|new college|graduate|university|early career|entry|junior|\bjr\b|associate|engineer i\b|\bi\b$|engineer 1\b|\b1\b$|level 1|l1\b|2026|2027|apprentice)', re.I)
TITLE_BAD = re.compile(r'(senior|\bsr\b|staff|principal|lead|manager|director|head of|architect|phd|\biii\b|\biv\b|\b3\b|clearance|ts/sci|secret|recruit|sales|account exec)', re.I)
US = re.compile(r'(united states|\busa?\b|remote|, ?(al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b|new york|san francisco|seattle|boston|austin|chicago|los angeles|denver|atlanta|bay area)', re.I)
NON_US = re.compile(r'(canada|toronto|vancouver|london|uk\b|united kingdom|india|bangalore|bengaluru|germany|berlin|ireland|dublin|poland|singapore|japan|tokyo|israel|tel aviv|mexico|brazil|australia|sydney|netherlands|amsterdam|paris|france|spain|philippines|remote - (emea|apac|latam))', re.I)

# The profile can replace the default new-grad software filters (targets.title_include / level_include / title_exclude).
sys.path.insert(0, HERE)
from jobprofile import load as _load
_T = _load(required=False).get('targets') or {}
_rx = lambda words: re.compile('(' + '|'.join(re.escape(w) for w in words) + ')', re.I)
if _T.get('title_include'): TITLE_OK = _rx(_T['title_include'])
if _T.get('level_include'): LEVEL_OK = _rx(_T['level_include'])
if _T.get('title_exclude'): TITLE_BAD = _rx(_T['title_exclude'])

SYSTEMS = '--systems' in sys.argv
SYS_OK = re.compile(r'(system(s)? engineer|systems? administrator|sysadmin|it engineer|it systems|infrastructure engineer|cloud (systems )?engineer|windows engineer|azure engineer|microsoft 365|m365|endpoint engineer|identity engineer|systems? analyst|it operations engineer|network(s)? engineer|servicenow (engineer|developer|administrator)|automation engineer)', re.I)

def keep(title, loc):
    if SYSTEMS:
        if not SYS_OK.search(title) or TITLE_BAD.search(title) or re.search(r'mechanical|electrical|hardware|rf |propulsion|avionics|manufacturing', title, re.I): return False
        if loc and NON_US.search(loc) and not re.search(r'united states|\busa?\b', loc, re.I): return False
        if loc and not US.search(loc): return False
        return True
    if not TITLE_OK.search(title) or TITLE_BAD.search(title): return False
    if not LEVEL_OK.search(title) and not re.fullmatch(r'\s*(software|backend|back-end|full[- ]?stack|frontend|front-end|platform|cloud|devops|infrastructure|machine learning|ml|ai|data|product|forward deployed|automation)( software)? (engineer|developer)\s*(\(.*\)|,.*|-.*)?', title, re.I): return False
    if loc and NON_US.search(loc) and not re.search(r'united states|\busa?\b', loc, re.I): return False
    if loc and not US.search(loc): return False
    return True

def crawl(b):
    p, t = b
    out = []
    try:
        if p == 'greenhouse':
            d = json.loads(get(f'https://boards-api.greenhouse.io/v1/boards/{t}/jobs'))
            for j in d.get('jobs', []):
                loc = (j.get('location') or {}).get('name', '')
                if keep(j['title'], loc):
                    out.append(dict(company=d.get('company', {}).get('name') or t, title=j['title'], url=j['absolute_url'], apply_url=j['absolute_url'], portal='greenhouse', location=loc, updated=j.get('first_published') or j.get('updated_at', ''), board=t))
        elif p == 'ashby':
            d = json.loads(get(f'https://api.ashbyhq.com/posting-api/job-board/{t}'))
            for j in d.get('jobs', []):
                loc = j.get('location', '') + (' remote' if j.get('isRemote') else '')
                if j.get('isListed', True) and keep(j['title'], loc):
                    out.append(dict(company=t, title=j['title'], url=j['jobUrl'], apply_url=j.get('applyUrl') or j['jobUrl'] + '/application', portal='ashby', location=loc, updated=j.get('publishedAt', ''), board=t))
        elif p == 'lever':
            d = json.loads(get(f'https://api.lever.co/v0/postings/{t}?mode=json'))
            for j in d:
                loc = (j.get('categories') or {}).get('location', '') or ''
                if keep(j['text'], loc):
                    out.append(dict(company=t, title=j['text'], url=j['hostedUrl'], apply_url=j['applyUrl'], portal='lever', location=loc, updated=str(j.get('createdAt', '')), board=t))
    except Exception:
        pass
    return out

with cf.ThreadPoolExecutor(24) as ex:
    res = [x for r in ex.map(crawl, sorted(boards)) for x in r]

apps = json.load(open(os.path.join(HERE, 'applications.json'), encoding='utf-8'))
seen_links = {re.sub(r'[?#].*$', '', a.get('link', '')).rstrip('/') for a in apps}
seen_cr = {(a['company'].lower()[:12], a['role'].lower()[:25]) for a in apps}
# Same posting can appear as .../<id>, .../<id>/application or .../apply: also match on the posting id itself.
POST_ID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|/jobs/(\d{6,})')
pid = lambda u: (lambda m: m and (m.group(1) or m.group(0)))(POST_ID.search(u or ''))
seen_ids = {pid(a.get('link')) for a in apps} - {None}
uniq, keys = [], set()
for r in res:
    k = re.sub(r'[?#].*$', '', r['url']).rstrip('/')
    if k in keys or k in seen_links or pid(r['url']) in seen_ids or (r['company'].lower()[:12], r['title'].lower()[:25]) in seen_cr:
        continue
    keys.add(k); uniq.append(r)
for r in uniq: r['leveled'] = bool(LEVEL_OK.search(r['title']))
uniq.sort(key=lambda r: (r['leveled'], r.get('updated', '')), reverse=True)
json.dump(uniq, open(os.path.join(HERE, 'candidates_systems.json' if SYSTEMS else 'candidates.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('candidates', len(uniq))
from collections import Counter
print(Counter(r['portal'] for r in uniq))
