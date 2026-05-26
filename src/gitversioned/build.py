"""Wrapping PEP 517 build backend for GitVersioned.

This module acts as a PEP 517 compliant build backend that intercepts build hook
invocations, runs the version resolution and file generation/injection, and then
delegates execution to the actual target build backend (e.g. Hatchling, Setuptools,
or Maturin).
"""

from __future__ import annotations

import contextlib
import importlib
from typing import Any

from loguru import logger

from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_and_generate_version


class _BuildState:
    target_backend: Any = None
    version_resolved: bool = False


def _ensure_version_resolved() -> None:
    """Run GitVersioned version resolution and file generation/injection once."""
    if _BuildState.version_resolved:
        return

    _BuildState.version_resolved = True

    try:
        # Load settings
        settings = Settings()
        project_root = settings.project_root

        # Instantiate objects explicitly
        repository = GitRepository(project_root)
        environment = BuildEnvironment(project_root=project_root)

        # Resolve and generate version
        version, path = resolve_and_generate_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        logger.info(f"[gitversioned.build] Resolved version: {version}")
        if path:
            logger.info(f"[gitversioned.build] Generated version file at: {path}")
    except Exception as err:
        msg = "[gitversioned.build] Failed during version resolution/generation"
        logger.exception(msg)
        raise RuntimeError(
            f"GitVersioned failed to resolve/generate version: {err}"
        ) from err


def _get_target_backend() -> Any:
    """Retrieve the target build backend to delegate to."""
    if _BuildState.target_backend is not None:
        return _BuildState.target_backend

    backend_str = None
    with contextlib.suppress(Exception):
        settings = Settings()
        backend_str = settings.build_backend

    if not backend_str:
        backend_str = "setuptools.build_meta"

    logger.debug(f"[gitversioned.build] Delegating to build backend: {backend_str}")

    try:
        # Split module name and object path if any (e.g. setuptools.build_meta)
        module_name = backend_str
        obj_name = None
        if ":" in backend_str:
            module_name, obj_name = backend_str.split(":", 1)

        module = importlib.import_module(module_name)  # nosemgrep
        _BuildState.target_backend = getattr(module, obj_name) if obj_name else module
    except Exception as err:
        logger.exception(
            f"[gitversioned.build] Failed to import target backend {backend_str}"
        )
        raise ImportError(
            f"Could not import build backend '{backend_str}': {err}"
        ) from err

    return _BuildState.target_backend


def __getattr__(name: str) -> Any:
    """Dynamically delegate hooks to the target build backend."""
    if not name.startswith("__"):
        _ensure_version_resolved()
        backend = _get_target_backend()
        return getattr(backend, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    """Expose the target backend's hooks when dir() is called on the module."""
    backend_dir = []
    with contextlib.suppress(Exception):
        backend = _get_target_backend()
        backend_dir = dir(backend)

    # Combine this module's globals with the target backend's globals
    custom_dir = set(globals().keys()) | set(backend_dir)
    return sorted(custom_dir)
