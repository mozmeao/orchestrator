# Builder stage - for compiling dependencies
FROM python:3.13-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and compilation script
COPY requirements/ requirements/
COPY bin/compile-requirements.sh bin/compile-requirements.sh
RUN chmod +x bin/compile-requirements.sh

# Install uv for fast dependency compilation
RUN pip install --upgrade pip uv

# Final stage - runtime image
FROM python:3.13-slim

ARG GIT_SHA=latest
ENV GIT_SHA=${GIT_SHA}

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements/requirements.txt

# Copy project files
COPY . .

# Make all scripts executable
RUN chmod +x /app/bin/*.sh

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["/app/bin/run-dev.sh"]
