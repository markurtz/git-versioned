# Use a slim Python image
FROM python:3.10-slim

# Version build argument to be injected via GitVersioned overrides
ARG VERSION="0.0.0"
ENV APP_VERSION=$VERSION

# Install tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY . .

# Create a secure non-root user
RUN useradd -u 10001 -m appuser && \
    chown -R appuser: /app

USER appuser

# Disable healthcheck since this is a simple run-once example script
HEALTHCHECK NONE

# Check current version variables
CMD echo "Running Maturin Polyglot Overrides App version: $APP_VERSION"
