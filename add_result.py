"""Append one application result to applications.json and the activity log.

Usage: python3 -I add_result.py '<json row>'
Row keys: company, role, location, pay, portal, status (Applied|Skipped), link, notes, and for submitted jobs resume_tex.
id, applied (today), track and resume_file are filled in. Re-reads applications.json right before writing
(other runs write it too) and refuses duplicates by id or link.
"""
import datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from activity_log import log_event

APPS = os.path.join(HERE, 'applications.json')


def main():
    r = json.loads(sys.argv[1])
    r['id'] = re.sub(r'[^a-z0-9]+', '-', (r['company'] + ' ' + r['role']).lower()).strip('-')[:60]
    r.setdefault('applied', datetime.date.today().isoformat())
    r.setdefault('track', 'Internship' if re.search(r'intern|co-?op', r['role'], re.I) else 'New grad')
    tex = r.get('resume_tex', '')
    r['resume_file'] = os.path.basename(tex)[:-4] + '.pdf' if tex else ''
    r.setdefault('resume_url', '')
    apps = json.load(open(APPS, encoding='utf-8'))
    key = lambda u: re.sub(r'[?#].*$', '', u or '').rstrip('/')
    if any(a['id'] == r['id'] or (r.get('link') and key(a.get('link')) == key(r['link'])) for a in apps):
        print('DUPLICATE, not added:', r['id'])
        return
    apps.append(r)
    json.dump(apps, open(APPS, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    kind = 'apply' if r['status'] == 'Applied' else 'skip'
    log_event(kind, f"{r['company']} - {r['role']}: {r['status']}" + ('' if kind == 'apply' else f" ({r.get('notes', '')[:200]})"), url=r.get('link', ''))
    print('added', r['id'], r['status'])


if __name__ == '__main__':
    main()
