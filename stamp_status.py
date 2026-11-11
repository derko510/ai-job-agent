"""Keeps status.json, the dashboard's "last updated" stamps: one row per thing that updates.

Rows: {"key": "applications", "at": ..., "applied": N}  - when the applications data last actually changed (sync_dashboard.py)
      {"key": "email", "at": ...}                       - when Gmail was last checked for replies (the 6-hour email check)
Usage: python -I stamp_status.py email
"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'status.json')


def stamp(key, **extra):
    try:
        rows = json.load(open(PATH, encoding='utf-8'))
    except (OSError, ValueError):
        rows = []
    rows = [r for r in rows if r.get('key') not in (key, 'updated')]  # 'updated' was the old single stamp
    rows.append({'key': key, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), **extra})
    rows.sort(key=lambda r: r['key'])
    json.dump(rows, open(PATH, 'w', encoding='utf-8'))


def has(key):
    try:
        return any(r.get('key') == key for r in json.load(open(PATH, encoding='utf-8')))
    except (OSError, ValueError):
        return False


if __name__ == '__main__':
    stamp(sys.argv[1])
    print('stamped', sys.argv[1])
