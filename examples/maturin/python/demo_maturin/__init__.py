"""A Rust extension versioned from git tags."""

from __future__ import annotations

from demo_maturin._native import __version__, add

__all__ = ["__version__", "add"]
