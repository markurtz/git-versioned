"""
Maturin Polyglot Overrides example package.
"""

from __future__ import annotations

try:
    from .version import __version__
except ImportError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
