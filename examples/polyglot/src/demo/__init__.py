"""The Python package at the root of a polyglot repository."""

from __future__ import annotations

try:
    from demo.version import __version__
except ImportError:  # a source checkout that has not been built or stamped
    __version__ = "0.0.0"

__all__ = ["__version__"]
