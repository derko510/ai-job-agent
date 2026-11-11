"""Capture the job description for every application that was sent (any status except Skipped).

Writes jds.json: [{id, company, role, jd, source, captured}]. Incremental: rows already captured are kept.
Sources: Greenhouse boards-api, Ashby posting-api, Lever postings api, UnitedHealth Group careers page.
Run: python -I fetch_jds.py
"""
import json, os, re, sys, html, datetime, urllib.request, concurrent.futures as cf
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'jds.json')
MAX = 12000

def get(u, t=25):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=t).read().decode('utf-8', 'replace')

def text(h):
    h = html.unescape(h or '')
    h = re.sub(r'(?is)<(script|style).*?</\1>', '', h)
    h = re.sub(r'(?i)<li[^>]*>', '\n- ', h)
    h = re.sub(r'(?i)<br\s*/?>|</(p|div|h[1-6]|ul|ol|li|tr)>', '\n', h)
    h = re.sub(r'<[^>]+>', '', h)
    h = html.unescape(h).replace('\xa0', ' ')
    h = re.sub(r'[ \t]+', ' ', h)
    h = re.sub(r'\n\s*\n\s*\n+', '\n\n', h)
    return h.strip()

_ashby = {}
def ashby_board(org):
    if org not in _ashby:
        _ashby[org] = json.loads(get(f'https://api.ashbyhq.com/posting-api/job-board/{org}')).get('jobs', [])
    return _ashby[org]

def fetch(link, company):
    link = link or ''
    m = re.search(r'greenhouse\.io/(?:embed/job_app\?for=)?([A-Za-z0-9_-]+)/jobs/(\d+)', link) or re.search(r'greenhouse\.io/embed/job_app\?for=([A-Za-z0-9_-]+).*?token=(\d+)', link)
    if m:
        d = json.loads(get(f'https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}'))
        return text(d.get('content')), 'greenhouse'
    m = re.search(r'jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})', link)
    if m:
        for j in ashby_board(m.group(1)):
            if j.get('id') == m.group(2):
                return (j.get('descriptionPlain') or text(j.get('descriptionHtml'))), 'ashby'
        return '', 'ashby (posting closed)'
    m = re.search(r'jobs\.lever\.co/([^/?#]+)/([0-9a-f-]{36})', link)
    if m:
        d = json.loads(get(f'https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}'))
        parts = [d.get('descriptionPlain') or '']
        for l in d.get('lists') or []:
            parts.append(l.get('text', '') + '\n' + text(l.get('content')))
        parts.append(d.get('additionalPlain') or '')
        return '\n\n'.join(p for p in parts if p).strip(), 'lever'
    m = re.search(r'gh_jid=(\d+)', link)
    if m:  # company-hosted Greenhouse page: guess the board token from the company name
        for tok in {re.sub(r'[^a-z0-9]', '', company.lower().split('(')[0]), company.lower().split()[0]}:
            try:
                d = json.loads(get(f'https://boards-api.greenhouse.io/v1/boards/{tok}/jobs/{m.group(1)}'))
                return text(d.get('content')), 'greenhouse'
            except Exception:
                pass
    if 'careers.unitedhealthgroup.com/job/' in link:
        h = get(link)
        m = re.search(r'(?is)<div[^>]+class="[^"]*ats-description[^"]*"[^>]*>(.*?)</section>', h) or re.search(r'(?is)<section[^>]+job-description[^>]*>(.*?)</section>', h)
        return (text(m.group(1)) if m else ''), 'unitedhealthgroup'
    return '', 'not captured (portal needs login or unknown)'

def main():
    apps = json.load(open(os.path.join(HERE, 'applications.json'), encoding='utf-8'))
    have = {r['id']: r for r in json.load(open(OUT, encoding='utf-8'))} if os.path.exists(OUT) else {}
    todo = [a for a in apps if a.get('status') != 'Skipped' and not (have.get(a['id']) or {}).get('jd')]
    now = datetime.date.today().isoformat()
    def work(a):
        try:
            jd, src = fetch(a.get('link', ''), a.get('company', ''))
        except Exception as e:
            jd, src = '', 'not captured (' + type(e).__name__ + ')'
        return dict(id=a['id'], company=a['company'], role=a['role'], jd=(jd or '')[:MAX], source=src, captured=now)
    with cf.ThreadPoolExecutor(12) as ex:
        for r in ex.map(work, todo):
            if r['jd'] or r['id'] not in have:
                have[r['id']] = r
    keep = {a['id'] for a in apps if a.get('status') != 'Skipped'}
    rows = [r for i, r in have.items() if i in keep]
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print('jds', len(rows), 'with text', sum(bool(r['jd']) for r in rows), 'new', len(todo), 'bytes', os.path.getsize(OUT))

if __name__ == '__main__':
    main()
