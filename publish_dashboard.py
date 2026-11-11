"""Every-30-minute dashboard refresh, built to use as little AI as possible.

Usage: python -I publish_dashboard.py        -> syncs (no AI) and prints NOCHANGE or PUBLISH <json plan>
       python -I publish_dashboard.py --done -> records that the plan was published

1. Runs sync_dashboard.py (plain Python, no AI): merges batch results, rebuilds resumes/JDs/public files, writes status.json.
2. Only if a published file actually changed since the last publish, calls headless Claude on Haiku with an exact,
   step-by-step publish recipe (upload changed files + one ArtifactData batch). No changes -> no AI call at all.
Logs to logs/publish.log. Run: python -I publish_dashboard.py
"""
import datetime, hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from jobprofile import load as _load
URL = _load(required=False).get('dashboard_url', '')  # set by setup
# published file -> dataset id / published name
FILES = {
    'applications_public.json': ('applications', 'applications.json'),
    'resumes.json': ('resumes', 'resumes.json'),
    'jds.json': ('jds', 'jds.json'),
    'oas.json': ('oas', 'oas.json'),
    'calls.json': ('calls', 'calls.json'),
    'answers.json': ('answers', 'answers.json'),
    'activity_public.json': ('activity', 'activity.json'),
    'status.json': ('status', 'status.json'),
}
STATE = os.path.join(HERE, 'logs', 'publish_state.json')
LOG = os.path.join(HERE, 'logs', 'publish.log')


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")
    print(msg)


def digest(p):
    if not os.path.exists(p):
        return ''
    if p.endswith('activity_public.json'):
        # Ignore the log's own "dashboard refreshed" entries (and the window sliding as they're added), or every publish
        # would trigger the next one: only the newest real events count.
        ev = [[e.get('at'), e.get('kind'), e.get('msg')] for e in json.load(open(p, encoding='utf-8')) if e.get('kind') != 'publish'][:50]
        return hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    # Telegram reminders for upcoming calls and test deadlines; never blocks the sync.
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'reminders.py')], cwd=HERE, capture_output=True)
    today = datetime.date.today().isoformat()
    env = dict(os.environ, SYNC_DATE=today)
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'sync_dashboard.py')], cwd=HERE, env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    log('sync: ' + (r.stdout.strip().splitlines() or ['(no output)'])[-1])

    old = json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else {}
    changed = [f for f in FILES if os.path.exists(os.path.join(HERE, f)) and digest(os.path.join(HERE, f)) != old.get(f)]
    if not changed:
        log('nothing changed since last publish')
        print('NOCHANGE')
        return
    plan = [{'file': os.path.join(HERE, f), 'dataset': FILES[f][0], 'name': FILES[f][1]} for f in changed]
    json.dump(plan, open(os.path.join(HERE, 'logs', 'publish_plan.json'), 'w', encoding='utf-8'), indent=1)
    log(f'PUBLISH NEEDED: {len(plan)} files')
    try:
        sys.path.insert(0, HERE); from activity_log import log_event; log_event('publish', f'dashboard refresh: {len(plan)} files changed')
    except Exception: pass
    print('PUBLISH ' + json.dumps(plan))


def mark_done():
    new = {f: digest(os.path.join(HERE, f)) for f in FILES}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(new, open(STATE, 'w', encoding='utf-8'), indent=1)
    log('publish recorded as done')

if __name__ == '__main__':
    mark_done() if '--done' in sys.argv else main()
