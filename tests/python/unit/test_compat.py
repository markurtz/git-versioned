from __future__ import annotations

import importlib
import sys
import types
from typing import Any, cast

import pytest

from gitversioned import compat


@pytest.fixture(autouse=True, scope="module")
def restore_compat_module() -> Any:
    """Fixture to restore the original sys.modules and compat module state."""
    original_opentelemetry = sys.modules.get("opentelemetry")
    original_opentelemetry_trace = sys.modules.get("opentelemetry.trace")
    original_psutil = sys.modules.get("psutil")
    original_tomllib = sys.modules.get("tomllib")
    original_tomli = sys.modules.get("tomli")

    yield

    # Restore the original modules in sys.modules
    for module_name, module_ref in [
        ("opentelemetry", original_opentelemetry),
        ("opentelemetry.trace", original_opentelemetry_trace),
        ("psutil", original_psutil),
        ("tomllib", original_tomllib),
        ("tomli", original_tomli),
    ]:
        if module_ref is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = module_ref

    # Reload compat to restore original state
    importlib.reload(compat)


@pytest.mark.smoke
def test_smoke_module_exports() -> None:
    """Verify that compat exposes the expected variables and matches expected types."""
    assert compat.__all__ == ["opentelemetry_trace", "psutil", "tomllib"]
    assert hasattr(compat, "opentelemetry_trace")
    assert hasattr(compat, "psutil")
    assert hasattr(compat, "tomllib")


@pytest.mark.sanity
def test_sanity_opentelemetry_trace_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify opentelemetry_trace is correctly resolved when available."""
    mock_module = types.ModuleType("opentelemetry.trace")
    monkeypatch.setitem(sys.modules, "opentelemetry", types.ModuleType("opentelemetry"))
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", mock_module)
    importlib.reload(compat)
    assert compat.opentelemetry_trace is mock_module


@pytest.mark.regression
def test_regression_opentelemetry_trace_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify opentelemetry_trace resolves to None when unavailable."""
    monkeypatch.setitem(sys.modules, "opentelemetry", cast("Any", None))
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", cast("Any", None))
    importlib.reload(compat)
    assert compat.opentelemetry_trace is None


@pytest.mark.sanity
def test_sanity_psutil_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify psutil is correctly resolved when available."""
    mock_module = types.ModuleType("psutil")
    monkeypatch.setitem(sys.modules, "psutil", mock_module)
    importlib.reload(compat)
    assert compat.psutil is mock_module


@pytest.mark.regression
def test_regression_psutil_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify psutil resolves to None when unavailable."""
    monkeypatch.setitem(sys.modules, "psutil", cast("Any", None))
    importlib.reload(compat)
    assert compat.psutil is None


@pytest.mark.sanity
def test_sanity_tomllib_native_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tomllib uses native standard library when available."""
    mock_tomllib = types.ModuleType("tomllib")
    monkeypatch.setitem(sys.modules, "tomllib", mock_tomllib)
    monkeypatch.setitem(sys.modules, "tomli", cast("Any", None))
    importlib.reload(compat)
    assert compat.tomllib is mock_tomllib


@pytest.mark.sanity
def test_sanity_tomli_fallback_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tomllib falls back to tomli when native tomllib is unavailable."""
    mock_tomli = types.ModuleType("tomli")
    monkeypatch.setitem(sys.modules, "tomllib", cast("Any", None))
    monkeypatch.setitem(sys.modules, "tomli", mock_tomli)
    importlib.reload(compat)
    assert compat.tomllib is mock_tomli


@pytest.mark.regression
def test_regression_tomllib_all_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify tomllib resolves to None.

    This runs when both native tomllib and tomli are unavailable.
    """
    monkeypatch.setitem(sys.modules, "tomllib", cast("Any", None))
    monkeypatch.setitem(sys.modules, "tomli", cast("Any", None))
    importlib.reload(compat)
    assert compat.tomllib is None
