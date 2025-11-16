# ElderCare Agent - Production Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY tests/ ./tests/

# Create necessary directories
RUN mkdir -p logs data/databases

# Make Python packages available
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port for Flask app
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Run as non-root user for security (optional, enable in production)
# RUN useradd -m -u 1000 eldercare && chown -R eldercare:eldercare /app
# USER eldercare

# Set Flask environment variables
ENV FLASK_APP=src.app
ENV FLASK_ENV=production
ENV PORT=8080

# Start Flask application
CMD exec gunicorn --bind :$PORT --workers 4 --threads 8 --timeout 0 src.app:app
