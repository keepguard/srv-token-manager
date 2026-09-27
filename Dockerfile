# syntax=docker/dockerfile:1
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install poetry with pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install poetry==1.8.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies with poetry cache
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY app/ ./app/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create secure directory
RUN mkdir -p /app/secure

# Expose port
EXPOSE 8700

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8700/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8700"]
