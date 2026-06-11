FROM python:3.11-slim

# The version of the application passed as a build argument
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}

LABEL version="${APP_VERSION}"

CMD ["python", "-c", "import os; print(f'Running version {os.environ.get(\"APP_VERSION\")}')"]
