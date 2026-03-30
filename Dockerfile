# Use Python 3.10+ slim image as base
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ make \
    libopenblas-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn

# Copy project files
COPY . .

# Create logs and models cache directories
RUN mkdir -p logs models_cache

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV ARIA_HOST=0.0.0.0
ENV ARIA_PORT=8000
ENV ARIA_LOG_LEVEL=info
ENV ARIA_EXECUTION_MODE=dynamic_layers
ENV ARIA_WORKERS=4

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the FastAPI server with Gunicorn
CMD ["gunicorn", \
     "api.server:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--access-logfile", "logs/access.log", \
     "--error-logfile", "logs/error.log", \
     "--log-level", "info"]

