"""Unit tests for the resolved version record."""

from __future__ import annotations

import pytest

from gitversioned.model import Version
from gitversioned.resolve import Resolved


def _resolved(sha: str | None) -> Resolved:
    return Resolved(
        version=Version.parse("1.0.0"),
        type="dev",
        source="tag",
        tag="v1.0.0",
        base=Version.parse("1.0.0"),
        distance=1,
        sha=sha,
        date=None,
        dirty=[],
    )


class TestShortSha:
    """The commit hash as it appears in the local part of a version."""

    @pytest.mark.smoke
    def test_seven_characters(self) -> None:
        """A hash is shortened to seven characters."""
        assert _resolved("abc1234def5678").short_sha == "abc1234"
        assert _resolved("1234567def5678").short_sha == "1234567"
        assert _resolved(None).short_sha is None

    @pytest.mark.regression
    def test_leading_zero_digits_are_lengthened(self) -> None:
        """An all-digit value with a leading zero would be renumbered by pip."""
        assert _resolved("0123456789abcdef").short_sha == "0123456789a"
        assert _resolved("0123456f").short_sha == "0123456f"
        assert _resolved("0abc1234").short_sha == "0abc123"
