"""Send the candidate a Telegram message (only to their own chat). Optional: does nothing until set up.

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env.telegram (the candidate creates it; see .env.telegram.example)
and only sends when profile.json has notifications.telegram = true.
Usage:
  python -I notify.py "text"                 send one message
  python -I notify.py --key <id> "text"      send once per key (deduped via notified.json)
"""
import json, os, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SENT = os.path.join(HERE, 'notified.json')


def env():
    vals = {}
    p = os.path.join(HERE, '.env.telegram')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals.get('TELEGRAM_BOT_TOKEN'), vals.get('TELEGRAM_CHAT_ID')


def enabled():
    from jobprofile import load
    return bool((load(required=False).get('notifications') or {}).get('telegram'))


def send(text):
    if not enabled():
        print('telegram is off (profile notifications.telegram = false); not sent')
        return False
    tok, chat = env()
    if not tok or not chat:
        print('telegram not configured (.env.telegram missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)')
        return False
    data = urllib.parse.urlencode({'chat_id': chat, 'text': text[:4000], 'disable_web_page_preview': 'true'}).encode()
    try:
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data=data, timeout=20).read()
        return True
    except Exception as e:
        print('telegram send failed:', type(e).__name__)
        return False


def once(key, text):
    done = set(json.load(open(SENT, encoding='utf-8'))) if os.path.exists(SENT) else set()
    if key in done:
        return
    if send(text):
        done.add(key)
        json.dump(sorted(done), open(SENT, 'w', encoding='utf-8'))
        print('sent', key)


if __name__ == '__main__':
    args = sys.argv[1:]
    if args[:1] == ['--pending']:
        pass  # email-code pings are off: code-gated applications are skipped, never finished by hand
    elif args[:1] == ['--key'] and len(args) >= 3:
        once(args[1], ' '.join(args[2:]))
    elif args:
        send(' '.join(args))
