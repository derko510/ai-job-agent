"""Log what changed in the tracker and send Telegram alerts for the few things that matter.

Called by sync_dashboard.py after every sync. Compares applications.json with the last snapshot:
- every newly logged application/skip  -> activity log (no Telegram)
- status moves to Recruiter Screen / Interview / Offer -> activity log + Telegram (once per job)
Also exports logs for the dashboard's Activity panel.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_log import log_event, export_public
import notify

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, 'logs', 'status_snapshot.json')
BIG = {'Recruiter Screen': '📞 Recruiter screen', 'Interview': '🎯 Interview', 'Offer': '🎉 OFFER'}


def run():
    apps = json.load(open(os.path.join(HERE, 'applications.json'), encoding='utf-8'))
    first = not os.path.exists(SNAP)
    old = {} if first else json.load(open(SNAP, encoding='utf-8'))
    for a in apps:
        prev, cur = old.get(a['id']), a.get('status')
        if first or prev == cur:
            continue
        who = f"{a.get('company')} - {a.get('role')}"
        if prev is None:
            kind = {'Applied': 'apply', 'Skipped': 'skip', 'Ready': 'block'}.get(cur, 'apply')
            log_event(kind, f"{who}: {cur}", note=(a.get('notes') or '')[-200:])
        else:
            log_event('status', f"{who}: {prev} -> {cur}")
        if cur in BIG and prev != cur:
            notify.once(f"status:{a['id']}:{cur}", f"{BIG[cur]}: {who}\nCheck the dashboard for details and prep notes.")
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    json.dump({a['id']: a.get('status') for a in apps}, open(SNAP, 'w', encoding='utf-8'))
    export_public()


if __name__ == '__main__':
    run()
