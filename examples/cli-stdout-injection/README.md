# CLI Stdout Output and Docker Injection Example

This example demonstrates how to resolve repository versions using the GitVersioned CLI and output them directly to stdout. This is especially useful for injecting versions into other tools, such as CI pipelines or Docker builds, without writing temporary files.

## Commands

To output the version with a custom template string:

```bash
gitversioned --output sys.stdout --pattern-release "VERSION={version}" --pattern-dev "VERSION={version}"
```

## Docker Build Integration

You can pass the resolved version directly as a build argument in a docker build command:

```bash
docker build --build-arg VERSION=$(gitversioned --output sys.stdout --pattern-release "{version}" --pattern-dev "{version}") -t myapp:latest .
```

And in your `Dockerfile`:

```dockerfile
FROM python:3.11-slim
ARG VERSION
ENV APP_VERSION=$VERSION
...
```
