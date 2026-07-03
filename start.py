# Gaurav Singh Thakur — MIT License
#
# Production entry point for Railway/Docker.
# I use a Python script instead of a shell command so there are no
# variable-expansion surprises across container runtimes.
#
# Design goal: NEVER exit before the web server is listening. The health check
# only needs the process up on the right port, so seeding problems or a missing
# gunicorn must not take the whole app down — they just get logged.

import os
import sys
import shutil
import subprocess

port = os.environ.get("PORT", "5000")
print(f"[start] python={sys.version.split()[0]} PORT={port} "
      f"DB_DIR={os.environ.get('DB_DIR', '(default)')}", flush=True)

# Try to seed, but keep going even if it fails. The app also runs init_db() at
# import, so the schema still gets created; worst case we start with no sample data.
try:
    print("[start] seeding database...", flush=True)
    r = subprocess.run([sys.executable, "seed.py"])
    print(f"[start] seed finished (exit {r.returncode})", flush=True)
except Exception as e:
    print(f"[start] seed raised {e!r} — continuing anyway", flush=True)

gunicorn_path = shutil.which("gunicorn")

if gunicorn_path:
    print(f"[start] launching gunicorn ({gunicorn_path}) on 0.0.0.0:{port}", flush=True)
    # os.execv with the resolved absolute path — no PATH-lookup surprises
    os.execv(gunicorn_path, [
        gunicorn_path,
        "--bind", f"0.0.0.0:{port}",
        "--workers", "1",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "app:app",
    ])
else:
    # Gunicorn isn't available — fall back to Flask's server so the app still
    # comes up. Fine for a single-kitchen prototype; the health check will pass.
    print("[start] gunicorn not found — falling back to Flask's built-in server", flush=True)
    from app import app
    app.run(host="0.0.0.0", port=int(port))
