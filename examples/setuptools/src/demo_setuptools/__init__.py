"""A setuptools project versioned from git tags."""

from __future__ import annotations

try:
    from demo_setuptools.version import __version__
except ImportError:  # a source checkout that has not been built or stamped
    __version__ = "0.0.0"

__all__ = ["__version__"]
