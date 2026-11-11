"""Daily read of the SimplifyJobs New-Grad-Positions list (github.com/SimplifyJobs/New-Grad-Positions) — no AI.

Parses every open listing, keeps postings from the last few days that pass the profile's location rule and that the candidate hasn't
applied to yet, and splits them into:
  - ready:   on Greenhouse / Ashby / Lever (the batch can apply to these automatically)
  - account: Workday, iCIMS, Oracle, amazon.jobs, company career sites... (need the candidate's own sign-in; listed for them)
Returns both lists; job_scan.py merges `ready` into the next queue and mentions big names from `account` on Telegram.
"""
import html, json, os, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from locations import location_ok

URL = 'https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md'
BIG = re.compile(r'\b(google|alphabet|meta|facebook|apple|amazon|aws|microsoft|netflix|nvidia|openai|anthropic|'
                 r'salesforce|adobe|oracle|ibm|intel|uber|lyft|airbnb|stripe|linkedin|snap|tesla|spacex|databricks)\b', re.I)
TITLE_BAD = re.compile(r'\b(senior|sr\.?|staff|principal|lead|manager|director|phd)\b', re.I)


def clean(s):
    s = re.sub(r'<br\s*/?>', ', ', s or '')
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).replace('🔥', '').strip(' ,')


def portal_of(u):
    return 'greenhouse' if 'greenhouse.io' in u else 'ashby' if 'ashbyhq.com' in u else 'lever' if 'lever.co' in u else 'other'


def scan(max_age_days=4):
    text = urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read().decode('utf-8', 'replace')
    apps = json.load(open(os.path.join(HERE, 'applications.json'), encoding='utf-8'))
    seen_links = {re.sub(r'[?#].*$', '', a.get('link', '')).rstrip('/') for a in apps}
    seen_cr = {(a['company'].lower()[:12], a['role'].lower()[:25]) for a in apps}
    ready, account, last_co = [], [], ''
    for row in re.findall(r'<tr>(.*?)</tr>', text, re.S):
        tds = re.findall(r'<td>(.*?)</td>', row, re.S)
        if len(tds) < 5:
            continue
        co = clean(tds[0])
        if co.startswith('↳') or not co:
            co = last_co
        last_co = co
        role, loc = clean(tds[1]), clean(tds[2])
        links = re.findall(r'href="([^"]+)"', tds[3])
        if not links or '🔒' in tds[3] or '🔒' in row:
            continue  # closed posting
        apply = re.sub(r'([?&])(utm_source|ref)=Simplify&?', r'\1', links[0]).rstrip('?&')
        age = re.search(r'(\d+)\s*d', clean(tds[4]))
        if age and int(age.group(1)) > max_age_days:
            continue
        if TITLE_BAD.search(role) or not location_ok(loc):
            continue
        key = re.sub(r'[?#].*$', '', apply).rstrip('/')
        if key in seen_links or (co.lower()[:12], role.lower()[:25]) in seen_cr:
            continue
        item = dict(company=co, title=role, location=loc, url=apply, apply_url=apply, portal=portal_of(apply),
                    board='simplify', source='SimplifyJobs New-Grad', remote=bool(re.search(r'remote', loc, re.I)), big=bool(BIG.search(co)))
        (ready if item['portal'] != 'other' else account).append(item)
    return ready, account


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    r, a = scan()
    print('ready', len(r), 'needs sign-in', len(a))
    for x in (r + a)[:15]:
        print('-', x['portal'], '|', x['company'], '|', x['title'], '|', x['location'])
