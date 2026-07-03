# Gaurav Singh Thakur — MIT License
#
# Used for Railway deployments and local Docker testing.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data directory — mount a Railway Volume at /app/data to persist the database across deploys
RUN mkdir -p /app/data

# DB_DIR tells the app where to write the SQLite file.
# Railway: mount a volume at /app/data. Local: defaults to the project root.
ENV DB_DIR=/app/data

EXPOSE 5000

# sh -c ensures && and $PORT expansion work correctly.
# Railway has no startCommand so it uses this CMD directly.
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app"]
