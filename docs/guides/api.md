# Python API Guide

`gitversioned` can be imported and executed programmatically in your custom Python tools, scripts, and build hooks. This guide provides detailed examples for the core resolution functions: `resolve_version`, `resolve_version_output`, and `resolve_version_output_to_stream`.

______________________________________________________________________

## 1. `resolve_version`

`resolve_version` is the core resolution entry point. It evaluates the project settings, queries the configured VCS or file sources, applies auto-incrementing logic, and returns a tuple containing:

- `version`: A packaging-compatible `Version` object representing the resolved version.
- `resolved_type`: A string representing the resolved build type (e.g. `"release"`, `"dev"`, `"pre"`).
- `git_ref`: An optional `GitReference` object containing detailed commit and tag metadata.

### Example Usage:

```python
# Copyright 2026 Mark Kurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    environment=environment,
)

print(f"Calculated Version: {version}")
print(f"Resolved build type: {resolved_type}")

if git_ref:
    print(f"Commit SHA: {git_ref.commit_sha}")
    print(f"Distance from last tag: {git_ref.distance_from_head}")
    print(f"Is HEAD commit: {git_ref.is_head_commit}")
```

______________________________________________________________________

## 2. `resolve_version_output`

`resolve_version_output` resolves the version and formats it according to the configured output strategy (e.g., matching the `release` or `dev` templates). It returns the rendered content string without writing any files to disk. It returns a tuple containing:

- `content`: The fully rendered version string or template content as a string.
- `version`: The resolved `Version` object.
- `resolved_type`: The resolved build type string.
- `git_ref`: The optional `GitReference` object.

### Example Usage:

```python
# Copyright 2026 Mark Kurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gitversioned import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version_output

settings = Settings()
repository = GitRepository(settings.project_root)
environment = BuildEnvironment(project_root=settings.project_root)

# Resolve and render the template output
content, version, resolved_type, git_ref = resolve_version_output(
    settings=settings,
    repository=repository,
    environment=environment,
)

print(f"Resolved version: {version}")
print("Formatted Content Output:")
print("-" * 40)
print(content)
print("-" * 40)
```

______________________________________________________________________

## 3. `resolve_version_output_to_stream`

`resolve_version_output_to_stream` resolves the version, renders it according to the configured output strategy, and writes the resulting formatted text directly to the target output file configured in the settings. It returns a tuple containing:

- `output_path`: The absolute path to the file written (or `None` if output writing was disabled).
- `content`: The formatted content string that was written.
- `version`: The resolved `Version` object.
- `resolved_type`: The resolved build type string.
- `git_ref`: The optional `GitReference` object.

### Example Usage:

```python
# Copyright 2026 Mark Kurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tempfile
from pathlib import Path

from gitversioned import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version_output_to_stream

# Customize output path programmatically using a temporary directory
with tempfile.TemporaryDirectory() as temp_dir:
    settings = Settings(
        project_root=Path(temp_dir),
        output="src/my_package/__version__.py",
    )
    repository = GitRepository(settings.project_root)
    environment = BuildEnvironment(project_root=settings.project_root)

    # Resolve, format, and write to disk
    output_path, content, version, resolved_type, git_ref = resolve_version_output_to_stream(
        settings=settings,
        repository=repository,
        environment=environment,
    )

    if output_path:
        print(f"Successfully generated version file at: {output_path}")
        print(f"Calculated Version: {version}")
    else:
        print("Writing version file was disabled (no output path set).")
```

______________________________________________________________________

## Configuring Programmable Logging

`gitversioned` uses `loguru` for structured internal logging. You can control logging behavior programmatically:

```python
# Copyright 2026 Mark Kurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from gitversioned.logging import LoggingSettings, configure_logger

# Enable verbose debug logs redirected to stderr
configure_logger(
    LoggingSettings(
        enabled=True,
        level="DEBUG",
        sink=sys.stderr,
    ),
)
```
