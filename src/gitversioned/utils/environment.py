"""
Build environment introspection utilities.

This module provides tools for extracting hardware, operating system, and
Continuous Integration (CI) metadata during the build process. It enables
reproducible and traceable builds by automatically capturing runtime
context into structured Pydantic models.
"""

from __future__ import annotations

import os
import platform
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from gitversioned.compat import psutil

__all__ = ["BuildEnvironment", "get_ci_info", "get_ram_gb", "get_user"]


def get_user() -> str:
    """
    Retrieve the current system or environment user.

    Attempts to use standard library OS queries first, falling back to
    common environment variables.

    Example:
        >>> get_user()
        'markkurtz'

    :return: The resolved username or "unknown" if undetermined.
    """
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def get_ci_info() -> tuple[bool, str | None]:
    """
    Determine if the current execution is within a recognized Continuous
    Integration environment.

    Queries standard environment variables to identify platforms like
    GitHub Actions, GitLab CI, and others.

    Example:
        >>> is_ci, provider = get_ci_info()
        >>> print(f"CI: {is_ci}, Provider: {provider}")
        CI: True, Provider: GitHub Actions

    :return: Tuple indicating CI presence and provider name if found.
    """
    providers = {
        "GITHUB_ACTIONS": ("true", "GitHub Actions"),
        "GITLAB_CI": (None, "GitLab CI"),
        "CIRCLECI": ("true", "CircleCI"),
        "TRAVIS": ("true", "Travis CI"),
        "JENKINS_URL": (None, "Jenkins"),
        "BITBUCKET_COMMIT": (None, "Bitbucket Pipelines"),
    }
    for env_var, (expected, name) in providers.items():
        val = os.environ.get(env_var)
        if val and (expected is None or val == expected):
            return True, name

    if os.environ.get("CI") in ("true", "1", "True"):
        return True, "Unknown CI"
    return False, None


def get_ram_gb() -> float:
    """
    Calculate the total available system memory in gigabytes.

    Relies on `psutil` if available in the environment.

    Example:
        >>> get_ram_gb()
        16.0

    :return: The total RAM in GB, or 0.0 if `psutil` is unavailable.
    """
    if psutil:
        return round(psutil.virtual_memory().total / (1024**3), 2)
    return 0.0


class BuildEnvironment(BaseModel):
    """
    Structured metadata representing the current system and build execution context.

    Captures environmental data such as OS details, hardware specs, and CI presence.
    Utilized to record the provenance of a build artifact for auditing and debugging.

    Example:
        >>> env = BuildEnvironment()
        >>> print(env.os_system)
        'Darwin'
    """

    model_config = ConfigDict(frozen=True)

    # --- System & OS ---
    hostname: str = Field(
        default_factory=socket.gethostname,
        description="The network hostname of the build machine.",
    )
    user: str = Field(
        default_factory=get_user,
        description="The system username executing the build process.",
    )
    os_system: str = Field(
        default_factory=platform.system,
        description="The operating system name (e.g., 'Linux', 'Darwin', 'Windows').",
    )
    os_release: str = Field(
        default_factory=platform.release,
        description="The operating system release version.",
    )
    os_version: str = Field(
        default_factory=platform.version,
        description="The operating system build or release date string.",
    )

    # --- Hardware ---
    cpu_arch: str = Field(
        default_factory=platform.machine,
        description="Hardware architecture of the build machine (e.g., 'x86_64').",
    )
    cpu_cores: int = Field(
        default_factory=lambda: os.cpu_count() or 0,
        description="The number of logical CPU cores available.",
    )
    total_ram_gb: float = Field(
        default_factory=get_ram_gb,
        description="The total available system RAM in gigabytes.",
    )

    # --- Runtime ---
    python_version: str = Field(
        default_factory=platform.python_version,
        description="The version of the Python runtime executing the build.",
    )
    python_implementation: str = Field(
        default_factory=platform.python_implementation,
        description="The specific Python implementation (e.g., 'CPython', 'PyPy').",
    )
    python_compiler: str = Field(
        default_factory=platform.python_compiler,
        description="The compiler string used to build the Python runtime.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this context was captured.",
    )

    # --- CI Context ---
    is_ci: bool = Field(
        default_factory=lambda: get_ci_info()[0],
        description="True if executing within a recognized CI environment.",
    )
    ci_provider: str | None = Field(
        default_factory=lambda: get_ci_info()[1],
        description="The name of the detected CI provider, or None if undetermined.",
    )

    # --- Path Context ---
    project_root: Path = Field(
        default_factory=Path.cwd,
        description="The root directory of the project where the build was initiated.",
    )

    build_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="A unique identifier generated for this specific build execution.",
    )

    def __str__(self) -> str:
        """Return a concise string representation."""

        ci_str = f" [CI: {self.ci_provider}]" if self.is_ci else " [Local]"
        return (
            f"BuildEnvironment({self.os_system} {self.os_release} {self.cpu_arch}, "
            f"Python {self.python_version}, project={self.project_root.name}, "
            f"id={self.build_id}){ci_str}"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return (
            f"BuildEnvironment("
            f"hostname={self.hostname!r}, user={self.user!r}, "
            f"os_system={self.os_system!r}, os_release={self.os_release!r}, "
            f"os_version={self.os_version!r}, "
            f"cpu_arch={self.cpu_arch!r}, cpu_cores={self.cpu_cores!r}, "
            f"total_ram_gb={self.total_ram_gb!r}, "
            f"python_version={self.python_version!r}, "
            f"python_implementation={self.python_implementation!r}, "
            f"python_compiler={self.python_compiler!r}, timestamp={self.timestamp!r}, "
            f"is_ci={self.is_ci!r}, ci_provider={self.ci_provider!r}, "
            f"project_root={self.project_root!r}, build_id={self.build_id!r}"
            f")"
        )
