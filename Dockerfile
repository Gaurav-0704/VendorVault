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

# DB_DIR tells the app where to write the SQLite file
ENV DB_DIR=/app/data

EXPOSE 5000

# Pure Python entry point — no shell variable expansion needed
CMD ["python", "start.py"]
