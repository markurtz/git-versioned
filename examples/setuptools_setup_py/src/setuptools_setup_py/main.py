"""
Runnable script for the Setuptools setup.py versioning demonstration.
"""

from __future__ import annotations

import sys

from setuptools_setup_py import __version__

__all__ = ["main"]


def main() -> None:
    """
    Main CLI execution entrypoint.
    """
    print(f"Setuptools Setup.py Example Version: {__version__}")
    sys.exit(0)


if __name__ == "__main__":
    main()
