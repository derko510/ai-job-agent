"""One append-only activity log for everything the job-hunt system does.

Every script (and every AI agent, via `python -I activity_log.py <kind> <message> [json-details]`) appends one JSON line to
logs/activity.jsonl:  {"at": ISO time, "kind": ..., "msg": ..., "details": {...}}
Kinds used: apply, skip, block, email, call, oa, scan, queue, publish, notify, safety, error.
"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'logs', 'activity.jsonl')


def log_event(kind, msg, **details):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    rec = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'kind': kind, 'msg': str(msg)[:500]}
    if details:
        rec['details'] = details
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return rec


def recent(n=400):
    if not os.path.exists(LOG):
        return []
    lines = open(LOG, encoding='utf-8').read().splitlines()[-n:]
    out = []
    for i, l in enumerate(lines):
        try:
            r = json.loads(l)
            r['id'] = f"{r.get('at','')}-{i}"
            r.pop('details', None)  # keep the public dashboard copy small and free of local paths
            out.append(r)
        except Exception:
            pass
    return out[::-1]


def export_public(path=None):
    """Write the latest events (newest first) for the dashboard's Activity panel."""
    path = path or os.path.join(HERE, 'activity_public.json')
    rows = recent()
    for r in rows:
        r['msg'] = r['msg'].replace('C:\\Users', '[local]').replace('C:/Users', '[local]')
    json.dump(rows, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return len(rows)


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        extra = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(log_event(sys.argv[1], sys.argv[2], **extra))
    else:
        print(__doc__)
