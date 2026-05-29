"""Tests for Pydantic utilities."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Annotated, Any, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError
from pydantic_core import CoreSchema, core_schema

from gitversioned.utils.pydantic import (
    EnsureBool,
    EnsureList,
    EnsurePath,
    coerce_bool,
    coerce_list,
    coerce_path,
)


class MockHandler:
    """Mock handler for Pydantic core schema generation."""

    def generate_schema(self, schema_type: Any) -> CoreSchema:
        """Generate a basic core schema for testing."""
        return core_schema.any_schema()


class IntListModel(BaseModel):
    """Pydantic model containing EnsureList[int]."""

    items: EnsureList[int]


class StrListModel(BaseModel):
    """Pydantic model containing EnsureList[str]."""

    items: EnsureList[str]


class BoolListModel(BaseModel):
    """Pydantic model containing EnsureList[bool]."""

    items: EnsureList[bool]


class PathListModel(BaseModel):
    """Pydantic model containing EnsureList[Path]."""

    items: EnsureList[Path]


class EnsureBoolModel(BaseModel):
    """Pydantic model containing EnsureBool."""

    flag: EnsureBool


class EnsurePathModel(BaseModel):
    """Pydantic model containing EnsurePath."""

    path: EnsurePath


class TestCoerceBool:
    """Test suite for the coerce_bool function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("t", True),
            ("y", True),
            ("TRUE ", True),
            (True, True),
        ],
    )
    def test_invocation(self, input_value: Any, expected_value: Any) -> None:
        """Test truthy values with coerce_bool."""
        assert coerce_bool(input_value) == expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("false", False),
            ("0", False),
            ("no", False),
            ("f", False),
            ("n", False),
            (" FALSE", False),
            (False, False),
        ],
    )
    def test_invocation_falsy(self, input_value: Any, expected_value: Any) -> None:
        """Test falsy values with coerce_bool."""
        assert coerce_bool(input_value) == expected_value

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            (5, 5),
            ("other", "other"),
            (None, None),
        ],
    )
    def test_invocation_fallback(self, input_value: Any, expected_value: Any) -> None:
        """Test untransformed fallback cases with coerce_bool."""
        assert coerce_bool(input_value) == expected_value


class TestCoercePath:
    """Test suite for the coerce_path function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("/my/path", Path("/my/path")),
            (" /my/path ", Path("/my/path")),
        ],
    )
    def test_invocation(self, input_value: Any, expected_value: Any) -> None:
        """Test standard string paths with coerce_path."""
        assert coerce_path(input_value) == expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            (Path("/my/path"), Path("/my/path")),
            (123, 123),
            (None, None),
        ],
    )
    def test_invocation_fallback(self, input_value: Any, expected_value: Any) -> None:
        """Test fallback behavior for coerce_path."""
        assert coerce_path(input_value) == expected_value


class TestCoerceList:
    """Test suite for the coerce_list function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("val_a, val_b, val_c", ["val_a", "val_b", "val_c"]),
            ("val_a", ["val_a"]),
            (["val_a", "val_b"], ["val_a", "val_b"]),
            (("val_a", "val_b"), ["val_a", "val_b"]),
            ({"val_a"}, ["val_a"]),
        ],
    )
    def test_invocation(self, input_value: Any, expected_value: list[Any]) -> None:
        """Test standard iterables and comma-separated inputs with coerce_list."""
        assert coerce_list(input_value) == expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            (123, [123]),
            (None, []),
        ],
    )
    def test_invocation_single(
        self, input_value: Any, expected_value: list[Any]
    ) -> None:
        """Test single-item and empty list fallbacks with coerce_list."""
        assert coerce_list(input_value) == expected_value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ("yes, no", [True, False]),
            (["1", "0"], [True, False]),
        ],
    )
    def test_invocation_with_coercer(
        self, input_value: Any, expected_value: list[Any]
    ) -> None:
        """Test coerce_list with item_pre_coercer set to coerce_bool."""
        assert coerce_list(input_value, item_pre_coercer=coerce_bool) == expected_value

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("input_value", "expected_value"),
        [
            ([["yes", "no"]], [[True, False]]),
        ],
    )
    def test_invocation_nested(
        self, input_value: Any, expected_value: list[Any]
    ) -> None:
        """Test nested list structures with coerce_list."""
        assert coerce_list(input_value, item_pre_coercer=coerce_bool) == expected_value

    @pytest.mark.regression
    def test_invalid(self) -> None:
        """Test handling of exception-throwing coercers in coerce_list."""

        def raising_coercer(val: Any) -> Any:
            raise ValueError("Invalid item")

        with pytest.raises(ValueError, match="Invalid item"):
            coerce_list("item1, item2", item_pre_coercer=raising_coercer)


class TestEnsureList:
    """Test suite for the EnsureList type wrapper."""

    @pytest.fixture(
        params=[
            [1, 2, 3],
            ["val_a", "val_b"],
            [True, False],
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> EnsureList[Any]:
        """Return valid instances of EnsureList."""
        return EnsureList(request.param)

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Test EnsureList class signature and method definition."""
        assert issubclass(EnsureList, list)
        sig = inspect.signature(EnsureList.__get_pydantic_core_schema__)
        assert "source_type" in sig.parameters
        assert "handler" in sig.parameters

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: EnsureList[Any]) -> None:
        """Test initialization of EnsureList with valid inputs."""
        assert isinstance(valid_instances, EnsureList)
        assert isinstance(valid_instances, list)
        assert list(valid_instances) == valid_instances

    @pytest.mark.regression
    def test_invalid_initialization_values(self) -> None:
        """Test initialization of EnsureList with invalid values."""
        with pytest.raises(TypeError):
            EnsureList(123)  # type: ignore

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test empty initialization of EnsureList."""
        instance = EnsureList()
        assert len(instance) == 0

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "source_type",
        [
            EnsureList[int],
            EnsureList,
            Annotated[EnsureList[bool], "meta"],
            Annotated[list[Path], "meta"],
        ],
    )
    def test___get_pydantic_core_schema__(self, source_type: Any) -> None:
        """Test generation of Pydantic core schema."""
        handler: Any = MockHandler()
        schema = EnsureList.__get_pydantic_core_schema__(source_type, handler)
        assert isinstance(schema, dict)
        assert schema["type"] == "function-before"

    @pytest.mark.smoke
    def test_marshalling(self, valid_instances: EnsureList[Any]) -> None:
        """Test validation and serialization of EnsureList in models."""
        if all(isinstance(item, int) for item in valid_instances) and valid_instances:
            model_class: type[BaseModel] = IntListModel
        elif (
            all(isinstance(item, bool) for item in valid_instances) and valid_instances
        ):
            model_class = BoolListModel
        else:
            model_class = StrListModel

        model = model_class.model_validate({"items": valid_instances})
        assert model.items == valid_instances

        dumped = model.model_dump()
        assert dumped["items"] == valid_instances

        json_data = model.model_dump_json()
        assert isinstance(json_data, str)
        assert json_data is not None

        model_int = IntListModel.model_validate({"items": "1, 2, 3"})
        assert model_int.items == [1, 2, 3]

        model_bool = BoolListModel.model_validate({"items": "yes, no, true, false"})
        assert model_bool.items == [True, False, True, False]

        model_path = PathListModel.model_validate({"items": "/path1, /path2"})
        assert model_path.items == [Path("/path1"), Path("/path2")]

    @pytest.mark.regression
    def test_invalid_marshalling(self) -> None:
        """Test model validation failures with invalid formats."""
        with pytest.raises(ValidationError):
            IntListModel.model_validate({"items": "val_a, val_b, val_c"})


@pytest.mark.smoke
def test_ensure_bool() -> None:
    """Validate metadata and happy paths for EnsureBool."""
    assert get_origin(EnsureBool) is Annotated
    args = get_args(EnsureBool)
    assert args[0] is bool

    assert EnsureBoolModel(flag="yes").flag is True
    assert EnsureBoolModel(flag="0").flag is False
    assert EnsureBoolModel(flag=True).flag is True


@pytest.mark.regression
@pytest.mark.parametrize("invalid_value", ["not_a_bool", [123]])
def test_ensure_bool_invalid(invalid_value: Any) -> None:
    """Validate failure pathways for EnsureBool."""
    with pytest.raises(ValidationError):
        EnsureBoolModel(flag=invalid_value)


@pytest.mark.smoke
def test_ensure_path() -> None:
    """Validate metadata and happy paths for EnsurePath."""
    assert get_origin(EnsurePath) is Annotated
    args = get_args(EnsurePath)
    assert args[0] is Path

    assert EnsurePathModel(path="/my/path").path == Path("/my/path")
    assert EnsurePathModel(path=Path("/my/path")).path == Path("/my/path")


@pytest.mark.regression
@pytest.mark.parametrize("invalid_value", [123, [456]])
def test_ensure_path_invalid(invalid_value: Any) -> None:
    """Validate failure pathways for EnsurePath."""
    with pytest.raises(ValidationError):
        EnsurePathModel(path=invalid_value)
