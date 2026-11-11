"""Convert a tailored resume .tex (Jake's-resume template) to structured JSON for the dashboard viewer.

Usage: python resume_to_json.py <file.tex>   -> prints JSON
Library: parse(tex_text) -> dict
"""
import json
import re
import sys


def _args(s, i, n):
    """Read n brace groups starting at/after index i. Returns (list, end_index)."""
    out = []
    while len(out) < n:
        while i < len(s) and s[i] != '{':
            i += 1
        if i >= len(s):
            break
        depth, j = 0, i
        while j < len(s):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(s[i + 1:j])
        i = j + 1
    return out, i


def clean(t):
    t = re.sub(r'\\href\{[^}]*\}\{(.*?)\}', r'\1', t)
    for cmd in ('textbf', 'underline', 'textit', 'emph', 'small', 'scshape', 'Huge'):
        t = re.sub(r'\\' + cmd + r'\{([^{}]*)\}', r'\1', t)
    t = t.replace('$|$', '|').replace('\\%', '%').replace('\\&', '&').replace('\\$', '$').replace('\\_', '_')
    t = re.sub(r'\\vspace\{[^}]*\}', '', t)
    t = re.sub(r'\\(small|scshape|Huge|large|\\)', ' ', t)
    t = t.replace('{', '').replace('}', '').replace('~', ' ')
    t = t.replace('--', '–')
    return re.sub(r'\s+', ' ', t).strip()


def section(tex, name):
    m = re.search(r'\\section\{' + name + r'\}(.*?)(?=\\section\{|\\end\{document\})', tex, re.S)
    return m.group(1) if m else ''


def items(block):
    res, i = [], 0
    while True:
        k = block.find('\\resumeItem{', i)
        if k < 0:
            break
        (a,), i = _args(block, k + len('\\resumeItem'), 1)
        res.append(clean(a))
    return res


def parse(tex):
    tex = re.sub(r'(?m)(?<!\\)%.*$', '', tex)  # drop comments
    body = tex[tex.index('\\begin{document}'):]
    head = re.search(r'\\begin\{center\}(.*?)\\end\{center\}', body, re.S).group(1)
    name = clean(re.search(r'\\textbf\{\\Huge \\scshape ([^}]*)\}', head).group(1))
    contact_raw = head.split('\\\\', 1)[1] if '\\\\' in head else ''
    contact = [clean(x) for x in clean(contact_raw).split('|') if clean(x)]

    def subheads(block):
        out, i = [], 0
        while True:
            k = block.find('\\resumeSubheading', i)
            if k < 0:
                break
            a, i = _args(block, k + len('\\resumeSubheading'), 4)
            nxt = block.find('\\resumeSubheading', i)
            seg = block[i: nxt if nxt >= 0 else len(block)]
            out.append(dict(org=clean(a[0]), where=clean(a[1]), title=clean(a[2]), dates=clean(a[3]), bullets=items(seg)))
        return out

    edu = [dict(school=x['org'], where=x['where'], degree=x['title'], dates=x['dates']) for x in subheads(section(body, 'Education'))]
    exp = subheads(section(body, 'Experience'))
    projects, pb, i = [], section(body, 'Projects'), 0
    while True:
        k = pb.find('\\resumeProjectHeading', i)
        if k < 0:
            break
        a, i = _args(pb, k + len('\\resumeProjectHeading'), 3)
        nxt = pb.find('\\resumeProjectHeading', i)
        seg = pb[i: nxt if nxt >= 0 else len(pb)]
        head_txt = clean(a[0])
        title, _, tech = head_txt.partition('|')
        projects.append(dict(title=title.strip(), tech=tech.strip(), dates=clean(a[1]), role=clean(a[2]), bullets=items(seg)))
    skills = []
    for m in re.finditer(r'\\textbf\{([^}]*)\}\{:\s*([^}]*)\}', section(body, 'Technical Skills')):
        skills.append(dict(label=clean(m.group(1)), items=clean(m.group(2))))
    return dict(name=name, contact=contact, education=edu, experience=exp, projects=projects, skills=skills)


if __name__ == '__main__':
    print(json.dumps(parse(open(sys.argv[1], encoding='utf-8').read()), indent=1, ensure_ascii=False))
