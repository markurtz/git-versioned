"""
Runnable script for the Setuptools setup.cfg versioning demonstration.
"""

from __future__ import annotations

import sys

from setuptools_setup_cfg import __version__

__all__ = ["main"]


def main() -> None:
    """
    Main CLI execution entrypoint.
    """
    print(f"Setuptools Example Version: {__version__}")
    sys.exit(0)


if __name__ == "__main__":
    main()
