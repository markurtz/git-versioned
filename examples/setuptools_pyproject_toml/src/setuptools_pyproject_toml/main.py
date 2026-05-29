"""
Runnable script for the Setuptools pyproject.toml versioning demonstration.
"""

from __future__ import annotations

import sys

from setuptools_pyproject_toml import __version__

__all__ = ["main"]


def main() -> None:
    """
    Main CLI execution entrypoint.
    """
    print(f"Setuptools Example Version: {__version__}")
    sys.exit(0)


if __name__ == "__main__":
    main()
