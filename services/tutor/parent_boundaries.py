"""Typed semantic Parent Boundary metadata from the one primary Tutor call."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


PARENT_BOUNDARY_SCHEMA_VERSION = "parent-boundary-v1"


class ParentBoundaryCategory(str, Enum):
    RELIGION = "RELIGION"
    SEXUAL_CONTENT = "SEXUAL_CONTENT"
    RELATIONSHIPS = "RELATIONSHIPS"
    POLITICS = "POLITICS"
    DEATH_GRIEF = "DEATH_GRIEF"
    FAMILY_FINANCES = "FAMILY_FINANCES"


class ParentBoundaryModelAction(str, Enum):
    ALLOW = "ALLOW"
    AGE_APPROPRIATE_ONLY = "AGE_APPROPRIATE_ONLY"
    REDIRECT_TO_PARENT = "REDIRECT_TO_PARENT"


class ParentBoundaryRedirectFragments(BaseModel):
    """Small model-authored fragments that the server may safely compose."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    acknowledgement: str = Field(min_length=1, max_length=160)
    parent_reference: str = Field(min_length=1, max_length=160)
    safe_offer: str = Field(min_length=1, max_length=160)


class ParentBoundaryDecision(BaseModel):
    """Semantic classification only; server-owned settings still decide enforcement."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    category: ParentBoundaryCategory | None
    applies: bool
    model_action: ParentBoundaryModelAction
    # Preserve structurally valid but overlong/unsafe fragments long enough for
    # deterministic server fallback without losing the semantic category.
    redirect: dict[str, str] | None

    @model_validator(mode="after")
    def decision_is_unambiguous(self) -> "ParentBoundaryDecision":
        if self.schema_version != PARENT_BOUNDARY_SCHEMA_VERSION:
            raise ValueError("Unsupported Parent Boundary schema version.")
        if self.applies and self.category is None:
            raise ValueError("An applicable Parent Boundary needs a category.")
        if not self.applies and (
            self.category is not None
            or self.model_action is not ParentBoundaryModelAction.ALLOW
            or self.redirect is not None
        ):
            raise ValueError("A non-applicable Parent Boundary must be an open decision.")
        return self


def parse_parent_boundary_decision(payload: object) -> ParentBoundaryDecision | None:
    """Treat missing, invalid, and ambiguous semantic metadata as open by default."""

    try:
        return ParentBoundaryDecision.model_validate(payload)
    except ValidationError:
        return None


def parse_redirect_fragments(payload: object) -> ParentBoundaryRedirectFragments | None:
    """A fragment failure never changes server policy; it selects the fixed fallback wording."""

    try:
        return ParentBoundaryRedirectFragments.model_validate(payload)
    except ValidationError:
        return None
