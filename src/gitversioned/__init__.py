"""
Opinionated PEP 440 Python versioning for Git repos and submodules.

Provides an automated, deterministic system for generating rich version information from
Git repository metadata. It enforces CI/User authority and creates version files with
deep metadata for auditability, integrating natively with Hatch and Setuptools.

Example:
::
    from gitversioned import Settings, resolve_version
    from gitversioned.utils import BuildEnvironment, GitRepository

    version, _, ref = resolve_version(
        Settings(), GitRepository(), BuildEnvironment()
    )
    print("Current version:", version)
"""

from __future__ import annotations

from .logging import LoggingSettings, configure_logger
from .settings import Settings
from .versioning import (
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)

__all__ = [
    "LoggingSettings",
    "Settings",
    "__version__",
    "configure_logger",
    "resolve_version",
    "resolve_version_output",
    "resolve_version_output_to_stream",
]

__version__ = "0.1.2.dev20260514+9eea393"

configure_logger()
