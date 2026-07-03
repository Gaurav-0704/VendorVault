# Gaurav Singh Thakur — MIT License
#
# Used for Railway deployments and local Docker testing.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker caches this layer separately
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY . .

# Data directory — mount a Railway Volume here to persist the SQLite file across deploys
RUN mkdir -p /app/data

# Tell the app where to store the database.
# In Railway, mount a Volume at /app/data so data survives redeploys.
ENV DB_DIR=/app/data

EXPOSE 5000

# For local Docker use. Railway overrides this with startCommand in railway.toml.
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 120 --access-logfile - --error-logfile - app:app"]
