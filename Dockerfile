FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Cloud Run uses PORT env variable
ENV PORT=8080

# Run with gunicorn for production
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
