"""
Opinionated PEP 440 Python versioning for Git repos and submodules.

Provides an automated, deterministic system for generating rich version information from
Git repository metadata. It enforces CI/User authority and creates version files with
deep metadata for auditability, integrating natively with Hatch and Setuptools.

Example:
::
    from gitversioned import Settings, resolve_version
    from gitversioned.utils import BuildEnvironment, GitRepository

    version, ref = resolve_version(
        Settings(), GitRepository(), BuildEnvironment()
    )
    print(f"Current version: {version}")
"""

from __future__ import annotations

from typing import Annotated

from .logging import LoggingSettings, configure_logger, logger
from .settings import Settings
from .versioning import (
    generate_version_py,
    resolve_and_generate_version,
    resolve_version,
)

__all__ = [
    "LoggingSettings",
    "Settings",
    "__version__",
    "configure_logger",
    "generate_version_py",
    "logger",
    "resolve_and_generate_version",
    "resolve_version",
]

__version__: Annotated[
    str,
    "The current version of the gitversioned package as a PEP 440 compliant string",
] = "0.1.1"

configure_logger()
