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

EXPOSE 5000

# startup.sh handles seeding safely before gunicorn starts
COPY startup.sh /startup.sh
RUN chmod +x /startup.sh

CMD ["/startup.sh"]
