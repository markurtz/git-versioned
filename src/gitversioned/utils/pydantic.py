"""
Pydantic helpers for GitVersioned.

Provides reusable validation and type-coercion helpers for Pydantic models.
Integrates directly with the Pydantic core schema to handle robust parsing
of configurations and environment variables, including string-to-list splitting
and truthy/falsy string coercion.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Generic, TypeVar, get_args, get_origin

from pydantic import BeforeValidator, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

__all__ = [
    "EnsureBool",
    "EnsureList",
    "EnsurePath",
    "coerce_bool",
    "coerce_list",
    "coerce_path",
]

TypeVarT = TypeVar("TypeVarT")


def coerce_bool(value: Any) -> bool | Any:
    """
    Normalize truthy/falsy strings to actual booleans.

    Example:
        >>> coerce_bool("yes")
        True
        >>> coerce_bool("0")
        False
        >>> coerce_bool(5)
        5

    :param value: The value to coerce.
    :return: The boolean equivalent if recognized, otherwise the original value.
    """
    if isinstance(value, str):
        cleaned_value = value.lower().strip()
        if cleaned_value in {"true", "1", "yes", "t", "y"}:
            return True
        if cleaned_value in {"false", "0", "no", "f", "n"}:
            return False
    return value


def coerce_path(value: Any) -> Path | Any:
    """
    Normalize string paths to Path objects.

    Example:
        >>> isinstance(coerce_path("/tmp/path "), Path)
        True

    :param value: The value to coerce into a path.
    :return: A Path object if the input is a string, otherwise the original value.
    """
    if isinstance(value, str):
        return Path(value.strip())
    return value


def coerce_list(
    value: Any, item_pre_coercer: Callable[[Any], Any] | None = None
) -> list[Any]:
    """
    Recursively transform input into a list.

    Splits comma-separated strings and applies an optional pre-coercer function
    to individual items.

    Example:
        >>> coerce_list("a, b, c")
        ['a', 'b', 'c']
        >>> coerce_list("yes, no", coerce_bool)
        [True, False]

    :param value: The value to coerce into a list.
    :param item_pre_coercer: Optional function to apply to each item.
    :return: A list of processed items.
    """
    if value is None:
        return []

    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    return [
        coerce_list(item, item_pre_coercer)
        if isinstance(item, (list, tuple, set)) and not isinstance(item, str)
        else (item_pre_coercer(item) if item_pre_coercer else item)
        for item in items
    ]


class EnsureList(list[TypeVarT], Generic[TypeVarT]):
    """
    A list subclass integrating directly with Pydantic Core Schema.

    Preprocesses inputs (such as comma-separated strings and nested iterables)
    and applies inner type coercion before final schema validation.

    Example:
        >>> from pydantic import BaseModel
        >>> class MyModel(BaseModel):
        ...     items: EnsureList[int]
        >>> model = MyModel(items="1, 2, 3")
        >>> model.items
        [1, 2, 3]
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """
        Create a schema that hooks a pre-validator into the Pydantic pipeline.

        Extracts the inner type constraint and constructs a validator that runs
        prior to Pydantic's core schema validation.

        :param source_type: The original type annotation.
        :param handler: The Pydantic core schema handler.
        :return: The constructed Pydantic core schema.
        """
        origin = get_origin(source_type)
        if origin is Annotated:
            base_type = get_args(source_type)[0]
            base_origin = get_origin(base_type)
            if base_origin in (list, tuple, set):
                base_args = get_args(base_type)
                inner_type = base_args[0] if base_args else Any
            else:
                inner_type = base_type
        else:
            type_arguments = get_args(source_type)
            inner_type = type_arguments[0] if type_arguments else Any

        pre_coercer_map: dict[Any, Callable[[Any], Any]] = {
            bool: coerce_bool,
            Path: coerce_path,
        }
        target_pre_coercer = pre_coercer_map.get(inner_type)
        final_list_schema = handler.generate_schema(list[inner_type])

        def before_validator_logic(
            value: Any, _info: core_schema.ValidationInfo
        ) -> Any:
            # Preprocess the value through coerce_list with target pre-coercer.
            return coerce_list(value, item_pre_coercer=target_pre_coercer)

        return core_schema.with_info_before_validator_function(
            before_validator_logic,
            final_list_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                list, when_used="json-unless-none"
            ),
        )


EnsureBool = Annotated[
    bool,
    BeforeValidator(coerce_bool),
    Field(
        description=(
            "Robust boolean type that coerces truthy/falsy strings into actual "
            "booleans, enabling flexible environment variable and config parsing."
        )
    ),
]

EnsurePath = Annotated[
    Path,
    BeforeValidator(coerce_path),
    Field(
        description=(
            "Robust Path type that coerces string paths into Path objects, "
            "enabling standardized filesystem references across configurations."
        )
    ),
]
