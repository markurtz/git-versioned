"""Example unit tests for the project."""

import pytest


@pytest.mark.smoke
def test_smoke_example() -> None:
    """A basic smoke test to ensure the unit test suite runs."""
    assert True


@pytest.mark.sanity
def test_sanity_example() -> None:
    """A sanity test for detailed unit testing."""
    assert True


@pytest.mark.regression
def test_regression_example() -> None:
    """A regression test for unit testing."""
    assert True
