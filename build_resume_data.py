"""Build resumes.json (structured resume content per submitted application) for the dashboard.
Each submitted application row carries resume_tex (path to the tailored .tex that was sent)."""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from resume_to_json import parse

apps = json.load(open(os.path.join(HERE, 'applications.json'), encoding='utf-8'))
out = []
for a in apps:
    if not a.get('resume_file'):
        continue
    tex = a.get('resume_tex') or ''
    if tex and not os.path.isabs(tex):
        tex = os.path.join(HERE, tex)
    if not tex or not os.path.exists(tex):
        print('MISSING TEX for', a['id']); continue
    r = parse(open(tex, encoding='utf-8').read())
    out.append(dict(id=a['id'], company=a['company'], role=a['role'], resume_file=a.get('resume_file', ''), resume_json=json.dumps(r, ensure_ascii=False)))
json.dump(out, open(os.path.join(HERE, 'resumes.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(len(out), 'resumes;', os.path.getsize(os.path.join(HERE, 'resumes.json')), 'bytes')
