# Simple Dockerfile demonstrating version replacement via GitVersioned overrides
FROM python:3.10-slim

# The version argument will be dynamically replaced by GitVersioned during builds
ARG VERSION="0.0.0"

LABEL version="$VERSION"
LABEL description="GitVersioned Setuptools Overrides Example App"

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir .

# Create a secure non-root user
RUN useradd -u 10001 -m appuser && \
    chown -R appuser: /app

USER appuser

# Disable healthcheck since this is a simple run-once example script
HEALTHCHECK NONE

CMD ["python", "-m", "setuptools_pyproject_overrides.main"]
