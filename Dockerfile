# Gaurav Singh Thakur — MIT License
#
# I use this for Railway deployments and local Docker testing.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker caches this layer separately
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Data directory — mount a Railway Volume here to persist the SQLite file across deploys
RUN mkdir -p /app/data

# Fix line endings on startup.sh in case it was committed with Windows CRLF
RUN sed -i 's/\r$//' startup.sh && chmod +x startup.sh

EXPOSE 5000

# Railway overrides this CMD with startCommand from railway.toml.
# This is for local Docker use only.
CMD ["sh", "-c", "DB_DIR=/app/data python seed.py && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app"]
