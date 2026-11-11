"""Telegram reminders for upcoming calls/interviews and coding-test deadlines (plain Python, no AI).

Runs every 30 minutes from publish_dashboard.py. Each reminder is sent once (deduped in notified.json):
- calls.json, status Scheduled: ~1 day before (when it is 2-26 h away) and 1 hour before. The 1-hour one is sent on the dot
  by a one-time scheduled trigger (`python -I reminders.py --call <id>`); the 30-minute check only backs it up (<= 60 min left)
- oas.json, status To do with a deadline: ~1 day before (2-26 h left) and a last call (<= 3 h left)
Run by hand: python -I reminders.py   |   one call's 1-hour reminder now: python -I reminders.py --call <id>
"""
import datetime as dt, json, os, sys
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import notify

PT = ZoneInfo('America/Los_Angeles')


def when(s):
    try:
        t = dt.datetime.fromisoformat(s)
        return t if t.tzinfo else t.replace(tzinfo=PT)
    except (TypeError, ValueError):
        return None


def fmt(t):
    return t.astimezone(PT).strftime('%a %b %-d, %-I:%M %p PT')


def load(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []


def main(only=None):
    now = dt.datetime.now(dt.timezone.utc)
    for c in load('calls.json'):
        t = when(c.get('when'))
        if c.get('status') != 'Scheduled' or not t or t < now or (only and c.get('id') != only):
            continue
        hours = (t - now).total_seconds() / 3600
        what = f"{c.get('company')} - {c.get('type') or 'call'} ({c.get('role', '')})"
        extra = '\n'.join(x for x in [c.get('format') and f"Format: {c['format']}", c.get('with') and f"With: {c['with']}",
                                      c.get('link') and f"Link: {c['link']}"] if x)
        if hours <= 1.0 or only:
            notify.once(f"remind:{c['id']}:{c['when']}:1h", f"⏰ In {max(1, round(hours * 60))} min: {what}\n{fmt(t)}\n{extra}\nPrep notes are on the dashboard.")
        elif 2 <= hours <= 26 and not only:
            notify.once(f"remind:{c['id']}:{c['when']}:1d", f"📅 Tomorrow-ish: {what}\n{fmt(t)}\n{extra}\nPrep notes are on the dashboard.")
    if only:
        return
    for o in load('oas.json'):
        t = when(o.get('deadline'))
        if o.get('status') != 'To do' or not t or t < now:
            continue
        hours = (t - now).total_seconds() / 3600
        what = f"{o.get('company')} - {o.get('assessment') or 'assessment'}"
        if hours <= 3:
            notify.once(f"remind:{o['id']}:{o['deadline']}:3h", f"⚠️ Due in {max(1, round(hours * 60))} min: {what}\nDeadline {fmt(t)}\n{o.get('link') or o.get('email') or ''}")
        elif 2 <= hours <= 26:
            notify.once(f"remind:{o['id']}:{o['deadline']}:1d", f"📝 Due within a day: {what}\nDeadline {fmt(t)}\n{o.get('notes') or ''}\n{o.get('link') or o.get('email') or ''}")


if __name__ == '__main__':
    main(sys.argv[2] if sys.argv[1:2] == ['--call'] and len(sys.argv) > 2 else None)
