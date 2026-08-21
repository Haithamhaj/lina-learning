"""Project-owned structured contract for Grade 5 Math semantic extraction."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


SEMANTIC_SCHEMA_VERSION = "grade5-math-semantic-schema-v1"
SemanticType = Literal[
    "UNIT",
    "LESSON",
    "CONCEPT",
    "OBJECTIVE",
    "DEFINITION",
    "EXPLANATION",
    "EXAMPLE",
    "EXERCISE",
    "VOCABULARY",
    "FIGURE",
    "TABLE",
    "FORMULA",
]


class SemanticContractError(ValueError):
    """Structured semantic output violates the project-owned contract."""


class SemanticExtractionItem(BaseModel):
    """One source-linked educational item emitted by the semantic route."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    semantic_key: str = Field(min_length=1, max_length=255)
    semantic_type: SemanticType
    title: str = Field(min_length=1, max_length=1000)
    description: str | None = Field(default=None, max_length=5000)
    normalized_concept_key: str | None = Field(default=None, max_length=255)
    parent_semantic_key: str | None = Field(default=None, max_length=255)
    structural_item_keys: list[str] = Field(min_length=1)
    sibling_order: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticExtractionOutput(BaseModel):
    """One bounded model response plus explicit source-range accounting."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[SEMANTIC_SCHEMA_VERSION]
    items: list[SemanticExtractionItem]
    unclassified_structural_item_keys: list[str] = Field(default_factory=list)


def parse_semantic_output(text: str) -> SemanticExtractionOutput:
    """Parse model text as the fixed semantic JSON contract, never heuristics."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise SemanticContractError("Semantic model output is not valid JSON.") from error
    try:
        return SemanticExtractionOutput.model_validate(payload)
    except ValidationError as error:
        raise SemanticContractError(f"Semantic model output violates schema: {error}") from error


def validate_semantic_output(
    output: SemanticExtractionOutput,
    *,
    available_structural_item_keys: set[str],
    allowed_parent_semantic_keys: set[str] | None = None,
) -> None:
    """Enforce source/parent/key validity and complete explicit batch accounting."""

    allowed_parent_semantic_keys = allowed_parent_semantic_keys or set()
    semantic_keys = [item.semantic_key for item in output.items]
    duplicate_key = next((key for key in semantic_keys if semantic_keys.count(key) > 1), None)
    if duplicate_key is not None:
        raise SemanticContractError(f"Duplicate semantic key {duplicate_key!r}.")

    emitted_keys = set(semantic_keys)
    for item in output.items:
        if item.parent_semantic_key is not None and item.parent_semantic_key not in (
            emitted_keys | allowed_parent_semantic_keys
        ):
            raise SemanticContractError(
                f"Semantic item {item.semantic_key!r} references missing parent "
                f"{item.parent_semantic_key!r}."
            )
        for source_key in item.structural_item_keys:
            if source_key not in available_structural_item_keys:
                raise SemanticContractError(
                    f"Semantic item {item.semantic_key!r} references unknown structural item "
                    f"{source_key!r}."
                )

    accounted = {
        source_key
        for item in output.items
        for source_key in item.structural_item_keys
    } | set(output.unclassified_structural_item_keys)
    unknown_unclassified = set(output.unclassified_structural_item_keys) - available_structural_item_keys
    if unknown_unclassified:
        raise SemanticContractError(
            "Semantic output marks unknown structural items unclassified: "
            f"{sorted(unknown_unclassified)!r}."
        )
    if accounted != available_structural_item_keys:
        missing = sorted(available_structural_item_keys - accounted)
        raise SemanticContractError(
            f"Semantic output has unaccounted structural items: {missing!r}."
        )
