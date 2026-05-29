"""
Setuptools setup.py integration example package initialization.
"""

from __future__ import annotations

try:
    from .version import __version__  # type: ignore # noqa: PGH003
except ImportError:
    __version__ = "0.0.0.dev0+unknown"

__all__ = ["__version__"]
