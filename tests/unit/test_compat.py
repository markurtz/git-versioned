from __future__ import annotations

import importlib
import sys
import types

import pytest

from gitversioned import compat

pytestmark = pytest.mark.sanity


@pytest.mark.parametrize(
    ("is_available", "expected_type"),
    [
        (True, types.ModuleType),
        (False, type(None)),
    ],
    ids=["available", "unavailable"],
)
def test_opentelemetry_trace(
    monkeypatch: pytest.MonkeyPatch,
    is_available: bool,
    expected_type: type,
) -> None:
    if is_available:
        mock_module = types.ModuleType("opentelemetry.trace")
        monkeypatch.setitem(
            sys.modules, "opentelemetry", types.ModuleType("opentelemetry")
        )
        monkeypatch.setitem(sys.modules, "opentelemetry.trace", mock_module)
    else:
        monkeypatch.setitem(
            sys.modules,
            "opentelemetry",
            None,  # type: ignore[assignment]
        )
        monkeypatch.setitem(
            sys.modules,
            "opentelemetry.trace",
            None,  # type: ignore[assignment]
        )

    importlib.reload(compat)
    assert isinstance(compat.opentelemetry_trace, expected_type)
    if is_available:
        assert compat.opentelemetry_trace is not None
        assert compat.opentelemetry_trace.__name__ == "opentelemetry.trace"


@pytest.mark.parametrize(
    ("is_available", "expected_type"),
    [
        (True, types.ModuleType),
        (False, type(None)),
    ],
    ids=["available", "unavailable"],
)
def test_psutil(
    monkeypatch: pytest.MonkeyPatch,
    is_available: bool,
    expected_type: type,
) -> None:
    if is_available:
        mock_module = types.ModuleType("psutil")
        monkeypatch.setitem(sys.modules, "psutil", mock_module)
    else:
        monkeypatch.setitem(sys.modules, "psutil", None)  # type: ignore[assignment]

    importlib.reload(compat)
    assert isinstance(compat.psutil, expected_type)
    if is_available:
        assert compat.psutil is not None
        assert compat.psutil.__name__ == "psutil"


@pytest.mark.parametrize(
    ("tomllib_available", "tomli_available", "expected_type", "expected_name"),
    [
        (True, False, types.ModuleType, "tomllib"),
        (False, True, types.ModuleType, "tomli"),
        (False, False, type(None), None),
    ],
    ids=["tomllib_available", "tomli_available", "none_available"],
)
def test_tomllib(
    monkeypatch: pytest.MonkeyPatch,
    tomllib_available: bool,
    tomli_available: bool,
    expected_type: type,
    expected_name: str | None,
) -> None:
    if tomllib_available:
        mock_tomllib = types.ModuleType("tomllib")
        monkeypatch.setitem(sys.modules, "tomllib", mock_tomllib)
    else:
        monkeypatch.setitem(sys.modules, "tomllib", None)  # type: ignore[assignment]

    if tomli_available:
        mock_tomli = types.ModuleType("tomli")
        monkeypatch.setitem(sys.modules, "tomli", mock_tomli)
    else:
        monkeypatch.setitem(sys.modules, "tomli", None)  # type: ignore[assignment]

    importlib.reload(compat)
    assert isinstance(compat.tomllib, expected_type)
    if expected_name is not None:
        assert compat.tomllib is not None
        assert compat.tomllib.__name__ == expected_name
