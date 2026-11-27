"""Command line entry point: ``text-stats --version`` or ``text-stats FILE``."""

import sys
from pathlib import Path

from text_stats import __version__, count


def main() -> None:
    """Print the version, or the counts for one file."""
    if sys.argv[1:] == ["--version"]:
        print(f"text-stats {__version__}")
        return
    words, lines = count(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"{words} words, {lines} lines")


if __name__ == "__main__":
    main()
