### Multi-stage Dockerfile for Flask app (production)
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc curl && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy app sources
COPY . /app

EXPOSE 5000

# Use gunicorn in production
CMD ["gunicorn", "run:app", "-w", "4", "-b", "0.0.0.0:5000", "--chdir", "/app"]
