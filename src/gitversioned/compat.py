"""
Compatibility abstractions for optional dependencies.

This module centralizes fallback logic for safely importing optional dependencies
like ``psutil``, ``opentelemetry``, and TOML parsers. It provides standardized
access points for these modules, avoiding scattered ``try-except`` blocks across
the codebase. Maintainers should import optional dependencies from this module
rather than attempting direct imports elsewhere.
"""

from __future__ import annotations

import importlib
import types
from typing import Annotated

__all__ = ["opentelemetry_trace", "psutil", "tomllib"]

_tomllib: types.ModuleType | None = None
try:
    _tomllib = importlib.import_module("tomllib")
except ImportError:
    try:
        _tomllib = importlib.import_module("tomli")
    except ImportError:
        _tomllib = None

_opentelemetry_trace: types.ModuleType | None = None
try:
    from opentelemetry import trace

    _opentelemetry_trace = trace
except ImportError:
    _opentelemetry_trace = None

_psutil: types.ModuleType | None = None
try:
    _psutil = importlib.import_module("psutil")
except ImportError:
    _psutil = None

opentelemetry_trace: Annotated[
    types.ModuleType | None,
    "Enables distributed tracing integration. Used for tracing execution paths "
    "when OpenTelemetry is present. Provides the ``opentelemetry.trace`` module "
    "or ``None``.",
] = _opentelemetry_trace

psutil: Annotated[
    types.ModuleType | None,
    "Enables retrieval of detailed system and process information. Used to monitor "
    "system context. Provides the ``psutil`` module or ``None``.",
] = _psutil

tomllib: Annotated[
    types.ModuleType | None,
    "Enables TOML file parsing. Used for reading configuration files like "
    "``pyproject.toml``. Provides the standard library ``tomllib``, the "
    "third-party ``tomli``, or ``None``.",
] = _tomllib
