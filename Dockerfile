# Gaurav Singh Thakur — MIT License
#
# I use this for Railway deployments and local Docker testing.
# Multi-stage isn't needed here — it's a pure Python app with no build artifacts.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Create a data directory for the SQLite file
RUN mkdir -p /app/data

EXPOSE 5000

# Seed the database on first run, then start the server.
# I use gunicorn in production instead of Flask's dev server.
CMD python seed.py && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 app:app
