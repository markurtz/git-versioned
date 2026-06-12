"""Compatibility abstractions for optional dependencies and packaging errors.

This module centralizes fallback logic for safely importing optional
dependencies such as ``psutil``, ``opentelemetry``, and TOML parsers.
By providing standardized module-level variables that resolve to either
the imported module or ``None``, it prevents scattered ``try-except``
blocks and import errors across the library.

In addition to optional dependencies, it abstracts differences in
packaging-related setup exception classes. It resolves and exposes
tools to check or raise setup errors compatible with both legacy
``distutils`` and modern ``setuptools``.
"""

from __future__ import annotations

import importlib
import types
from typing import Annotated, NoReturn

__all__ = [
    "is_distutils_setup_error",
    "maturin",
    "opentelemetry_trace",
    "psutil",
    "raise_distutils_setup_error",
    "tomllib",
]

_maturin: types.ModuleType | None = None
try:
    _maturin = importlib.import_module("maturin")
except ImportError:
    _maturin = None

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


def raise_distutils_setup_error(
    message: str, from_exception: Exception | None = None
) -> NoReturn:
    """Dynamically resolve and raise the appropriate setup error class.

    Resolves the setup error class by attempting to import
    ``setuptools.errors.SetupError``, falling back to
    ``distutils.errors.DistutilsSetupError``, and ultimately using the
    builtin ``Exception`` if neither is available. This avoids import-time
    monkeypatching race conditions with ``setuptools``.

    Example:
        >>> try:
        ...     # Perform some custom setup or build operation
        ...     pass
        ... except Exception as err:
        ...     raise_distutils_setup_error("Setup failed", from_exception=err)

    :param message: The descriptive error message to associate with the
        raised exception.
    :param from_exception: An optional exception instance to chain via
        ``raise ... from``.
    :raises Exception: The resolved setup error or a standard base
        ``Exception``.
    """
    try:
        import setuptools.errors  # noqa: PLC0415

        exc_class = setuptools.errors.SetupError
    except ImportError:
        try:
            import distutils.errors  # noqa: PLC0415

            exc_class = distutils.errors.DistutilsSetupError
        except ImportError:
            exc_class = Exception

    if from_exception is not None:
        raise exc_class(message) from from_exception
    raise exc_class(message)


def is_distutils_setup_error(error: Exception) -> bool:
    """Verify if an exception instance matches the resolved SetupError.

    Checks the given exception against ``setuptools.errors.SetupError`` and
    ``distutils.errors.DistutilsSetupError`` if their respective modules
    can be imported.

    Example:
        >>> try:
        ...     # Run packaging tool logic
        ...     pass
        ... except Exception as err:
        ...     if is_distutils_setup_error(err):
        ...         print("Packaging setup error detected")

    :param error: The exception instance to evaluate.
    :returns: ``True`` if the error is a setup error instance; otherwise
        ``False``.
    """
    try:
        import setuptools.errors  # noqa: PLC0415

        if isinstance(error, setuptools.errors.SetupError):
            return True
    except ImportError:
        pass

    try:
        import distutils.errors  # noqa: PLC0415

        if isinstance(error, distutils.errors.DistutilsSetupError):
            return True
    except ImportError:
        pass

    return False


maturin: Annotated[
    types.ModuleType | None,
    "Enables the maturin build backend wrapper. Provides the ``maturin`` "
    "module or ``None``.",
] = _maturin

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
