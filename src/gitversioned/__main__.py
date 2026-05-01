# ---------------------------------------------------------
# GitVersioned
# Licensed under the Apache License, Version 2.0
# ---------------------------------------------------------
"""Main entrypoint for the gitversioned package."""

from __future__ import annotations

import argparse
import logging
import sys
from importlib.metadata import PackageNotFoundError, version

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Get the package version."""
    try:
        return version("gitversioned")
    except PackageNotFoundError:
        return "unknown"


def main() -> int:
    """Execute the main routine."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        prog="gitversioned",
        description="Opinionated PEP 440 Python versioning tool for Git repos.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    subparsers.add_parser("init", help="Initialize the repository configuration")

    # generate command
    subparsers.add_parser("generate", help="Generate the version metadata")

    args = parser.parse_args()

    if args.command == "init":
        logger.info("Initializing repository... (Not implemented yet)")
        return 0
    elif args.command == "generate":
        logger.info("[INFO] Generating version... (Not implemented yet)")
        logger.info("[SUCCESS] version.py created! Version: 0.1.0 (Placeholder)")
        return 0
    elif args.command is None:
        parser.print_help()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
