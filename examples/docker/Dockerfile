# The service image. Its OCI version label is a literal, so gitversioned stamps
# it; the build argument carries the same version into the image.
FROM python:3.13-slim

ARG VERSION=0.0.0
ENV APP_VERSION=${VERSION}

LABEL org.opencontainers.image.title="relay" \
      org.opencontainers.image.version="0.0.0"

USER nobody

HEALTHCHECK --interval=30s --timeout=5s CMD ["sh", "-c", "test -n \"$APP_VERSION\""]

CMD ["sh", "-c", "echo relay $APP_VERSION"]
