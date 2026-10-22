# ==============================================================================
# BrandGuard AI - Production Dockerfile (FastAPI Backend)
# ==============================================================================
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install security updates and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create an unprivileged user for production security
RUN useradd -m -u 1001 brandguard && chown -R brandguard:brandguard /app
USER brandguard

# Copy application source code
COPY --chown=brandguard:brandguard app/ ./app

# Expose HTTP port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch uvicorn server
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
