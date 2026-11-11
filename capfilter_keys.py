"""Company keys for the per-company cap (shared by capfilter.py and build_apply_queue.py)."""
import re
# Board slugs that are really another company's name, e.g. {'thinkahead': 'ahead'}. Add pairs if the cap misses one.
ALIAS = {}
def norm(s):
    s = s.lower()
    toks = re.findall(r'[a-z0-9]+', s)
    for t in toks:
        if t in ALIAS: return ALIAS[t]
    return toks[0] if toks else s
BOARD = re.compile(r'(?:jobs\.ashbyhq\.com|greenhouse\.io|jobs\.lever\.co)/([A-Za-z0-9_.%-]+)')
def keys(company, link):
    # Company names vary ("Brain Co" vs "BrainCo"), so also key on the job-board slug from the link.
    ks = {norm(company), re.sub(r'[^a-z0-9]', '', company.lower())}
    m = BOARD.search(link or '')
    if m and m.group(1) not in ('embed', 'jobs'): ks.add('board:' + m.group(1).lower())
    return ks
