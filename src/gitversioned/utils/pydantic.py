"""
Pydantic helpers for GitVersioned.

This module provides reusable validation and type-coercion helpers for Pydantic
models, integrating directly with the Pydantic core schema for performance.
These helpers ensure robust parsing of configurations and environment variables,
supporting list parsing from strings and boolean evaluation of truthy/falsy strings.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Generic, TypeVar, get_args

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

    .. code-block:: python

        coerce_bool("yes")  # True
        coerce_bool("0")    # False
        coerce_bool(5)      # 5

    :param value: The value to coerce.
    :return: The boolean equivalent if recognizable, otherwise the original value.
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

    .. code-block:: python

        coerce_path("/tmp/path ")  # Path("/tmp/path")

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

    Splits strings by commas and applies an optional pre-coercer to items
    before they are passed to the final Pydantic validator.

    .. code-block:: python

        coerce_list("a, b, c")  # ["a", "b", "c"]
        coerce_list("yes, no", coerce_bool)  # [True, False]

    :param value: The value to coerce into a list.
    :param item_pre_coercer: Optional function to apply to each item.
    :return: A list of processed items.
    """
    if value is None:
        return []

    # 1. Normalize input sequence
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    processed_list: list[Any] = []

    # 2. Process items (Recursive + Pre-coercion)
    for item in items:
        if isinstance(item, (list, tuple, set)) and not isinstance(item, str):
            processed_list.append(coerce_list(item, item_pre_coercer))
        else:
            # Apply "dirty" coercion (like 'yes' -> True) before standard validation
            processed_item = item_pre_coercer(item) if item_pre_coercer else item
            processed_list.append(processed_item)

    return processed_list


class EnsureList(list[TypeVarT], Generic[TypeVarT]):
    """
    A list subclass that tightly integrates with Pydantic Core Schema.

    It preprocesses inputs (splitting strings, normalizing bools) before
    delegating the final strict validation to Pydantic's native schema.

    .. code-block:: python

        from pydantic import BaseModel

        class MyModel(BaseModel):
            items: EnsureList[int]

        model = MyModel(items="1, 2, 3")
        print(model.items)  # [1, 2, 3]
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """
        Create a schema that hooks a pre-validator into the Pydantic pipeline.

        :param source_type: The original type annotation.
        :param handler: The Pydantic core schema handler.
        :return: The constructed Pydantic core schema.
        """
        # Extract the inner type (e.g., int from EnsureList[int])
        type_arguments = get_args(source_type)
        inner_type: Any = type_arguments[0] if type_arguments else Any

        # Identify if we need 'special' help for types Pydantic is strict about.
        # Standard types like int, float, str are handled natively by Pydantic
        # once the string is split into a list.
        pre_coercer_map: dict[Any, Callable[[Any], Any]] = {
            bool: coerce_bool,
            Path: coerce_path,
        }
        target_pre_coercer = pre_coercer_map.get(inner_type)

        # This schema represents what we WANT the data to look like at the end.
        # By calling handler.generate_schema, we get Pydantic's native list logic.
        final_list_schema = handler.generate_schema(list[inner_type])

        def before_validator_logic(
            value: Any, _info: core_schema.ValidationInfo
        ) -> Any:
            """Preprocessing wrapper before handing off to Pydantic's core."""
            return coerce_list(value, item_pre_coercer=target_pre_coercer)

        # We wrap the native schema in a 'before' validator.
        # Pipeline: Raw Input -> before_validator_logic -> Native Pydantic list[T]
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
            "A robust boolean type that coerces common truthy/falsy "
            "strings into actual booleans before validation."
        )
    ),
]

EnsurePath = Annotated[
    Path,
    BeforeValidator(coerce_path),
    Field(
        description=(
            "A robust Path type that normalizes and strips whitespace "
            "from string paths before validation."
        )
    ),
]
