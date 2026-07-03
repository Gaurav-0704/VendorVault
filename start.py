# Gaurav Singh Thakur — MIT License
#
# Production/deploy entry point for Railway and Docker.
#
# I run Flask's own server here on purpose. gunicorn is UNIX-only, which means
# I can't reproduce its behaviour on my Windows machine — and every failed
# Railway deploy was on that one untested path. Flask's server I can test end
# to end locally, so this is the reliable choice for a single-kitchen prototype.
#
# The one rule: never exit before the server is listening. A seeding hiccup
# must not take the whole app down (the app also creates its schema at import).

import os
import sys
import subprocess

port = int(os.environ.get("PORT", "5000"))
print(f"[start] python={sys.version.split()[0]} PORT={port} "
      f"DB_DIR={os.environ.get('DB_DIR', '(default)')}", flush=True)

# Seed sample data, but keep going even if it fails.
try:
    print("[start] seeding database...", flush=True)
    r = subprocess.run([sys.executable, "seed.py"])
    print(f"[start] seed finished (exit {r.returncode})", flush=True)
except Exception as e:
    print(f"[start] seed raised {e!r} — continuing anyway", flush=True)

print(f"[start] starting Flask server on 0.0.0.0:{port}", flush=True)
from app import app
app.run(host="0.0.0.0", port=port, threaded=True)
