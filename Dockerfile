# ============================================
# Scoop AI Agent - Dockerfile
# Standard Python (no Node.js needed now)
# ============================================

FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Cloud Run port
ENV PORT=8080

# Run
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
