FROM python:3.10-slim

# The following build argument will be updated by GitVersioned overrides
ARG VERSION="0.0.0"

LABEL version=${VERSION}

WORKDIR /app
COPY dist/*.whl .
RUN pip install *.whl

# Create a secure, non-root user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -d /home/appuser -s /sbin/nologin appuser

# Switch to the non-root user
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python --version || exit 1

CMD ["python", "-m", "hatchling_docker_overrides.main"]
