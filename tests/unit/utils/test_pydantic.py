"""Tests for Pydantic utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from gitversioned.utils.pydantic import (
    EnsureBool,
    EnsureList,
    EnsurePath,
    coerce_bool,
    coerce_list,
    coerce_path,
)


class TestCoerceBool:
    """Test the coerce_bool module level function."""

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("t", True),
            ("y", True),
            ("TRUE ", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("f", False),
            ("n", False),
            (" FALSE", False),
            (True, True),
            (False, False),
            (5, 5),
            ("other", "other"),
            (None, None),
        ],
    )
    def test_invocation(self, input_value: Any, expected_value: Any) -> None:
        """Test coerce_bool behavior across common input structures."""
        assert coerce_bool(input_value) == expected_value


class TestCoercePath:
    """Test the coerce_path module level function."""

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("/my/path", Path("/my/path")),
            (" /my/path ", Path("/my/path")),
            (Path("/my/path"), Path("/my/path")),
            (123, 123),
            (None, None),
        ],
    )
    def test_invocation(self, input_value: Any, expected_value: Any) -> None:
        """Test coerce_path behavior across common input structures."""
        assert coerce_path(input_value) == expected_value


class TestCoerceList:
    """Test the coerce_list module level function."""

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("a, b, c", ["a", "b", "c"]),
            ("a", ["a"]),
            (["a", "b"], ["a", "b"]),
            (("a", "b"), ["a", "b"]),
            ({"a"}, ["a"]),
            (123, [123]),
            (None, []),
        ],
    )
    def test_invocation(self, input_value: Any, expected_value: Any) -> None:
        """Test coerce_list behavior across common input structures."""
        assert coerce_list(input_value) == expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "coercer", "expected_value"),
        [
            ("yes, no", coerce_bool, [True, False]),
            (["1", "0"], coerce_bool, [True, False]),
            ([["yes", "no"]], coerce_bool, [[True, False]]),
        ],
    )
    def test_invocation_with_coercer(
        self, input_value: Any, coercer: Any, expected_value: Any
    ) -> None:
        """Test coerce_list behavior with a custom item coercer."""
        assert coerce_list(input_value, item_pre_coercer=coercer) == expected_value


class TestEnsureList:
    """Test the EnsureList Pydantic generic list class."""

    @pytest.fixture(
        params=[
            ([1, 2, 3], [1, 2, 3]),
            (["a", "b"], ["a", "b"]),
            ((1, 2), [1, 2]),
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> tuple[Any, list[Any]]:
        """Return valid parameters for initializing the class."""
        return request.param  # type: ignore[no-any-return]

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Test the class signature and inheritance."""
        assert issubclass(EnsureList, list)
        assert hasattr(EnsureList, "__get_pydantic_core_schema__")

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: tuple[Any, list[Any]]) -> None:
        """Test basic native Python list initialization behavior."""
        input_value, expected_value = valid_instances
        instance = EnsureList(input_value)
        assert instance == expected_value

    @pytest.mark.smoke
    def test_marshalling(self) -> None:
        """Test the Pydantic integration for model schema processing."""

        class IntModel(BaseModel):
            items: EnsureList[int]

        class StrModel(BaseModel):
            items: EnsureList[str]

        class BoolModel(BaseModel):
            items: EnsureList[bool]

        class PathModel(BaseModel):
            items: EnsureList[Path]

        assert IntModel(items="1, 2, 3").items == [1, 2, 3]  # type: ignore[arg-type]
        assert IntModel(items=["1", 2, "3"]).items == [1, 2, 3]  # type: ignore[arg-type]
        assert StrModel(items="a, b").items == ["a", "b"]  # type: ignore[arg-type]
        assert BoolModel(items="yes, no").items == [True, False]  # type: ignore[arg-type]
        assert PathModel(items="/a, /b").items == [Path("/a"), Path("/b")]  # type: ignore[arg-type]

        parsed_int_model = IntModel.model_validate({"items": "1, 2, 3"})
        assert parsed_int_model.items == [1, 2, 3]

    @pytest.mark.sanity
    def test_invalid_marshalling(self) -> None:
        """Test failure points during Pydantic schema validation."""

        class DummyModel(BaseModel):
            items: EnsureList[int]

        with pytest.raises(ValidationError):
            DummyModel(items="a, b, c")  # type: ignore[arg-type]


class TestEnsureBool:
    """Test the EnsureBool Pydantic type."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("yes", True),
            ("no", False),
            (True, True),
            (False, False),
            ("1", True),
            ("0", False),
        ],
    )
    def test_param_EnsureBool(self, input_value: Any, expected_value: bool) -> None:  # noqa: N802
        """Test param correctly parses acceptable truthy and falsy values."""

        class DummyModel(BaseModel):
            flag: EnsureBool

        assert DummyModel(flag=input_value).flag is expected_value  # type: ignore[arg-type]
        assert DummyModel.model_validate({"flag": input_value}).flag is expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize("invalid_value", ["not_a_bool", []])
    def test_param_EnsureBool_invalid(self, invalid_value: Any) -> None:  # noqa: N802
        """Test failure instances when assigning invalid values."""

        class DummyModel(BaseModel):
            flag: EnsureBool

        with pytest.raises(ValidationError):
            DummyModel(flag=invalid_value)  # type: ignore[arg-type]


class TestEnsurePath:
    """Test the EnsurePath Pydantic type."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("/my/path", Path("/my/path")),
            (" /my/path ", Path("/my/path")),
            (Path("/my/path"), Path("/my/path")),
        ],
    )
    def test_param_EnsurePath(self, input_value: Any, expected_value: Path) -> None:  # noqa: N802
        """Test param correctly parses acceptable string inputs into Paths."""

        class DummyModel(BaseModel):
            path: EnsurePath

        assert DummyModel(path=input_value).path == expected_value  # type: ignore[arg-type]
        assert DummyModel.model_validate({"path": input_value}).path == expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize("invalid_value", [123, []])
    def test_param_EnsurePath_invalid(self, invalid_value: Any) -> None:  # noqa: N802
        """Test failure instances when assigning invalid values."""

        class DummyModel(BaseModel):
            path: EnsurePath

        with pytest.raises(ValidationError):
            DummyModel(path=invalid_value)  # type: ignore[arg-type]
