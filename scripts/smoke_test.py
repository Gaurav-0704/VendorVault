# Gaurav Singh Thakur — MIT License
#
# End-to-end smoke test. Starts the real app against a throwaway database and
# checks the things that actually matter: every endpoint responds, auth blocks
# what it should, and the optional AI layer degrades cleanly with no key.
#
# Run from the project root:
#     python scripts/smoke_test.py
#
# Exit code 0 = everything passed, 1 = something failed.

import os
import sys
import json
import time
import tempfile
import subprocess
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'http://localhost:5000'
USER, PW = 'owner', 'smoke-test-pass'

fails = []


def check(name, ok, detail=''):
    print(f'  {"OK  " if ok else "FAIL"}  {name}{" — " + detail if detail else ""}')
    if not ok:
        fails.append(name)


def request(opener, path, method='GET', body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    op = opener.open if opener else urllib.request.urlopen
    try:
        r = op(req, timeout=10)
        return r.getcode(), (json.loads(r.read()) if r.headers.get_content_type() == 'application/json' else {})
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read())
        except Exception:
            payload = {}
        return e.code, payload


def main():
    env = dict(os.environ)
    env['DB_DIR'] = tempfile.mkdtemp(prefix='vv_smoke_')
    env['APP_USERNAME'] = USER
    env['APP_PASSWORD'] = PW
    env['APP_SECRET_KEY'] = 'smoke-secret'

    proc = subprocess.Popen([sys.executable, 'app.py'], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(4)

        # --- public + auth gate ---
        print('\nHealth & auth:')
        c, _ = request(None, '/health')
        check('/health public when logged out', c == 200, f'got {c}')
        c, _ = request(None, '/api/dashboard')
        check('/api/* blocked when logged out', c == 401, f'got {c}')

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.open(BASE + '/login',
                    data=urllib.parse.urlencode({'username': USER, 'password': PW}).encode(),
                    timeout=5)

        # --- every core endpoint, logged in ---
        print('\nCore endpoints (authenticated):')
        endpoints = [
            '/api/dashboard', '/api/orders', '/api/menu', '/api/purchases',
            '/api/finance', '/api/finance/weekly-cycle', '/api/stock',
            '/api/expenses', '/api/reports', '/api/profits', '/api/cost-analysis',
            '/api/settings', '/api/network-info', '/api/whatsapp/config',
            '/api/whatsapp/messages',
        ]
        for ep in endpoints:
            c, _ = request(opener, ep)
            check(ep, c == 200, f'got {c}')

        # --- parser ---
        print('\nWhatsApp parser:')
        c, d = request(opener, '/api/whatsapp/parse', 'POST',
                       {'text': '2 veg noddles n 1 chiken 65 for Rahul'})
        items = [l['item'] for l in d.get('lines', [])]
        check('parses messy order', c == 200 and d.get('customer') == 'Rahul' and len(items) == 2,
              f'customer={d.get("customer")} items={items}')

        # --- AI layer degrades cleanly with no key ---
        print('\nAI layer (no key set):')
        c, d = request(opener, '/api/ai/status')
        check('status reports disabled', c == 200 and d.get('enabled') is False)
        c, d = request(opener, '/api/ai/digest')
        check('digest returns clean no-key response', c == 400 and d.get('error') == 'no_api_key')

        # --- AI key set / mask / delete ---
        print('\nAI key management:')
        c, _ = request(opener, '/api/settings/ai-key', 'PUT', {'key': 'sk-ant-smoke-1234'})
        check('save key', c == 200, f'got {c}')
        c, d = request(opener, '/api/settings')
        masked = d.get('ai_key_set') is True and 'smoke' not in d.get('ai_key_preview', '')
        check('key masked in settings', masked, f'preview={d.get("ai_key_preview")}')
        c, d = request(opener, '/api/ai/status')
        check('status flips to enabled', d.get('enabled') is True)
        request(opener, '/api/settings/ai-key', 'DELETE')
        c, d = request(opener, '/api/ai/status')
        check('status back to disabled after delete', d.get('enabled') is False)

    finally:
        proc.terminate()

    print('\n' + '=' * 44)
    print('ALL SMOKE TESTS PASSED' if not fails else f'FAILED: {", ".join(fails)}')
    print('=' * 44)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
