"""Build a 1-page resume tailored to one job from the base LaTeX resume (resumes/_base/resume_base.tex).

Usage: python -I tailor_resume.py spec.json

spec.json keys (all optional except company/slug):
  company, slug            -> output folder resumes/<company>_<slug>_<YYYY-MM>/Resume_<Name>_<company>.pdf
  skills: {Label: "comma list"}   replaces the text of the skills line whose bold label starts with Label
  experience_order: {"<Employer as written in the base>": [i, ...]}   new order of that job's bullets (0-based)
  project_order: [name, ...]      new order of project blocks, by project title
  replace: [[old, new], ...]      exact text swaps (each old must exist once)
Only reorders and rewords true content; never add skills, numbers or claims the base doesn't have.
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from jobprofile import first_last
BASE = HERE / "resumes" / "_base" / "resume_base.tex"
OUT_ROOT = HERE / "resumes"
PDFLATEX = shutil.which("pdflatex")


def reorder_items(tex, anchor, order):
    start = tex.index(anchor)
    lst = tex.index(r"\resumeItemListStart", start) + len(r"\resumeItemListStart")
    end = tex.index(r"\resumeItemListEnd", lst)
    items = re.findall(r"\\resumeItem\{.*?\}\s*(?=\\resumeItem|$)", tex[lst:end].strip() + "\n", re.S)
    items = [i.strip() for i in items]
    if sorted(order) != list(range(len(items))):
        raise SystemExit(f"order {order} doesn't cover {len(items)} bullets under {anchor}")
    body = "\n" + "\n".join("            " + items[i] for i in order) + "\n      "
    return tex[:lst] + body + tex[end:]


def reorder_projects(tex, names):
    head = tex.index(r"\section{Projects}")
    start = tex.index(r"\resumeSubHeadingListStart", head) + len(r"\resumeSubHeadingListStart")
    end = tex.index(r"\resumeSubHeadingListEnd", start)
    blocks = re.split(r"(?=\s*\\resumeProjectHeading)", tex[start:end])
    blocks = [b for b in blocks if r"\resumeProjectHeading" in b]
    by_name = {}
    for b in blocks:
        m = re.search(r"\\textbf\{([^}]*)\}", b)
        by_name[m.group(1)] = b.rstrip()
    if sorted(names) != sorted(by_name):
        raise SystemExit(f"project_order {names} must list exactly {list(by_name)}")
    return tex[:start] + "".join("\n" + by_name[n].lstrip("\n") for n in names) + "\n\n" + tex[end:]


def main():
    if not PDFLATEX:
        raise SystemExit("pdflatex not found: install TeX Live (e.g. apt install texlive-latex-extra) and retry")
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    tex = BASE.read_text(encoding="utf-8")
    for label, value in spec.get("skills", {}).items():
        pat = re.compile(r"(\\textbf\{" + re.escape(label) + r"[^}]*\}\{: )[^}]*(\})")
        if not pat.search(tex):
            raise SystemExit(f"no skills line {label}")
        tex = pat.sub(lambda m: m.group(1) + value + m.group(2), tex, count=1)
    for org, order in (spec.get("experience_order") or {}).items():
        tex = reorder_items(tex, "{" + org + "}", order)
    if "project_order" in spec:
        tex = reorder_projects(tex, spec["project_order"])
    for old, new in spec.get("replace", []):
        if tex.count(old) != 1:
            raise SystemExit(f"replace target must appear once: {old[:60]}")
        tex = tex.replace(old, new)

    company = re.sub(r"[^A-Za-z0-9]+", "", spec["company"])
    out = OUT_ROOT / f"{company}_{spec['slug']}_{date.today():%Y-%m}"
    out.mkdir(parents=True, exist_ok=True)
    name = f"Resume_{first_last()}_{company}"
    (out / f"{name}.tex").write_text(tex, encoding="utf-8")
    run = subprocess.run([PDFLATEX, "-interaction=nonstopmode", f"-jobname={name}", f"{name}.tex"],
                         cwd=out, capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Output written on .*?\((\d+) pages?", run.stdout, re.S)
    pages = int(m.group(1)) if m else 0
    for ext in (".aux", ".log", ".out"):
        (out / f"{name}{ext}").unlink(missing_ok=True)
    if pages != 1:
        raise SystemExit(f"compile gave {pages} pages; fix the spec\n{run.stdout[-1500:]}")
    print(out / f"{name}.pdf")


if __name__ == "__main__":
    main()
