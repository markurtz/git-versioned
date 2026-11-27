"""Count words and lines."""

from text_stats.version import __version__

__all__ = ["__version__", "count"]


def count(text: str) -> tuple[int, int]:
    """Return the number of words and lines in ``text``."""
    return len(text.split()), len(text.splitlines())
