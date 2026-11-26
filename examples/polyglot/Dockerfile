FROM python:3.13-slim

LABEL org.opencontainers.image.title="demo" \
      org.opencontainers.image.version="0.0.0"

USER nobody

HEALTHCHECK --interval=30s --timeout=5s CMD ["python", "-c", "import demo"]

CMD ["python", "-c", "import demo; print(demo.__version__)"]
