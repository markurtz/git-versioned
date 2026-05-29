"""
Core version resolution and output generation engine.

Provides entry points to resolve PEP 440 versions from Git repository state,
environment variables, and project settings. Exposes high-level functions to
resolve, format, and direct versions to targeted output files or streams.

Example:
    .. code-block:: python

        from gitversioned.settings import Settings
        from gitversioned.versioning import resolve_version_output_to_stream

        output_path, content, version, version_type, reference = (
            resolve_version_output_to_stream(Settings())
        )
"""

from __future__ import annotations

from .entrypoints import (
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)
from .sources import VersionResolutionError

__all__ = [
    "VersionResolutionError",
    "resolve_version",
    "resolve_version_output",
    "resolve_version_output_to_stream",
]
