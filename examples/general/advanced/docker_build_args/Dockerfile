FROM python:3.11-slim

# The version of the application passed as a build argument
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}

LABEL version="${APP_VERSION}"

# Create a secure, non-root user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -d /home/appuser -s /sbin/nologin appuser

# Switch to the non-root user
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python --version || exit 1

CMD ["python", "-c", "import os; print(f'Running version {os.environ.get(\"APP_VERSION\")}')"]
