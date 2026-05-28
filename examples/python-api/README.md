# GitVersioned Python API Example

This example demonstrates how to use the GitVersioned library programmatically in a Python script or custom build task.

## Programmatic API Usage

Instead of using the CLI or build backend wrapper, you can import and call version resolution functions directly:

```python
from gitversioned import Settings, resolve_version
from gitversioned.utils import BuildEnvironment, GitRepository

settings = Settings()
repo = GitRepository(settings.project_root)
env = BuildEnvironment(project_root=settings.project_root)

version, _, ref = resolve_version(settings, repo, env)
print(f"Resolved version: {version}")
```

## Running the Example

Run the script from the root of the repository:

```bash
python examples/python-api/main.py
```
