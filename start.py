# Gaurav Singh Thakur — MIT License
#
# Production entry point for Railway/Docker.
# I use a Python script instead of a shell command so there are no
# variable-expansion surprises across different container runtimes.

import os
import sys
import subprocess

# Seed the database — skips automatically if data already exists
print("Running seed...")
result = subprocess.run([sys.executable, "seed.py"])
if result.returncode != 0:
    print("Seed failed — aborting.")
    sys.exit(result.returncode)

# Read PORT the same way gunicorn would, but in Python so it's always correct
port = os.environ.get("PORT", "5000")
print(f"Starting gunicorn on port {port}...")

# exec replaces this process with gunicorn so signals work correctly
os.execvp("gunicorn", [
    "gunicorn",
    "--bind", f"0.0.0.0:{port}",
    "--workers", "1",
    "--timeout", "120",
    "--access-logfile", "-",
    "--error-logfile", "-",
    "app:app",
])
