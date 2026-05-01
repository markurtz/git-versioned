# ---------------------------------------------------------
# {{project_name}}  # noqa: ERA001
# Licensed under the Apache License, Version 2.0
# ---------------------------------------------------------
"""Main entrypoint for the {{project_name}} package."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def main() -> int:
    """Execute the main routine."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Hello from {{project_name}}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
