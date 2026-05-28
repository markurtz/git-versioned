# Python API Guide

`gitversioned` can be imported and executed programmatically in your custom Python tools, scripts, and build hooks. This guide shows how to initialize the settings, inspect the repository state, and resolve version strings.

______________________________________________________________________

## Basic API Resolution

To calculate the dynamic version programmatically, initialize the settings context and pass it to the core version resolution engine:

```python
from gitversioned import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version

# 1. Initialize configuration settings (loads pyproject.toml / env vars / defaults)
settings = Settings()

# 2. Initialize Git repository and environment helpers
repository = GitRepository(settings.project_root)
environment = BuildEnvironment(project_root=settings.project_root)

# 3. Resolve the version components
version, resolved_type, git_ref = resolve_version(
    settings=settings,
    repository=repository,
    environment=environment
)

print(f"PEP 440 Version: {version}")
print(f"Git reference: {git_ref.commit_sha if git_ref else 'None'}")
print(f"Resolved build type: {resolved_type}")
```

______________________________________________________________________

## Output Generation & Formatting

If you want to resolve the version and get the fully rendered file content (e.g. to write it yourself or stream it over a socket), use `resolve_version_output`:

```python
from gitversioned import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version_output

settings = Settings()
repository = GitRepository(settings.project_root)
environment = BuildEnvironment(project_root=settings.project_root)

# Resolve and format the strategy template
content, version, resolved_type, git_ref = resolve_version_output(
    settings=settings,
    repository=repository,
    environment=environment
)

print("Generated File Contents:\n")
print(content)
```

To let `gitversioned` resolve and write the file directly based on the active output strategy:

```python
from gitversioned import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version_output_to_stream

settings = Settings()
repository = GitRepository(settings.project_root)
environment = BuildEnvironment(project_root=settings.project_root)

# Resolves, formats, writes to settings.output, and returns written path
output_path, content, version, resolved_type, git_ref = resolve_version_output_to_stream(
    settings=settings,
    repository=repository,
    environment=environment
)

if output_path:
    print(f"Successfully generated version file at: {output_path}")
```

______________________________________________________________________

## Configuring Programmable Logging

`gitversioned` uses `loguru` for structured internal logging. You can control logging behavior programmatically:

```python
import sys
from gitversioned.logging import LoggingSettings, configure_logger

# Enable verbose debug logs redirected to stderr
configure_logger(
    LoggingSettings(
        enabled=True,
        level="DEBUG",
        sink=sys.stderr
    )
)
```
