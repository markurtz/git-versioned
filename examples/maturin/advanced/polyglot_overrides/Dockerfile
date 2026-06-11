FROM python:3.10-slim

# The following build argument will be updated by GitVersioned overrides
ARG VERSION="0.0.0"

LABEL version=${VERSION}

WORKDIR /app
COPY dist/*.whl .
RUN pip install *.whl

CMD ["python", "-m", "maturin_polyglot_overrides.main"]
