"""Example end-to-end tests for the project."""

import pytest


@pytest.mark.smoke
@pytest.mark.e2e
def test_smoke_e2e_example() -> None:
    """A basic smoke test for end-to-end functionality."""
    assert True


@pytest.mark.sanity
@pytest.mark.e2e
def test_sanity_e2e_example() -> None:
    """A sanity test for end-to-end functionality."""
    assert True


@pytest.mark.regression
@pytest.mark.e2e
def test_regression_e2e_example() -> None:
    """A regression test for end-to-end functionality."""
    assert True
