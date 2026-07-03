#!/bin/sh
# Gaurav Singh Thakur — MIT License
#
# Seeds the database if needed, then starts gunicorn.
# Using a separate script so a seed failure doesn't silently swallow the error
# and so gunicorn always gets a clean start.

set -e

export DB_DIR=/app/data

echo "Running seed..."
python seed.py
echo "Seed done. Starting gunicorn..."

exec gunicorn \
  --bind "0.0.0.0:${PORT:-5000}" \
  --workers 1 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
