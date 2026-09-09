"""Declarative, renderer-free Agentic Canvas contracts and Tutor projection."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AGENTIC_CANVAS_SCENE_VERSION = "agentic-canvas-scene-v1"
AGENTIC_CANVAS_ACTION_VERSION = "agentic-canvas-action-v1"


class AgenticCanvasElementV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    label: str = Field(min_length=1, max_length=160)
    current_value: str | None = Field(..., max_length=240)


class AgenticCanvasBlockV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    block_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    type: Literal["MATH_BOARD", "SCENE_2D", "DIAGRAM", "TEXT_INTERACTION", "MATH_INPUT", "IMAGE"]
    meaning: str = Field(min_length=1, max_length=500)
    elements: list[AgenticCanvasElementV1] = Field(..., max_length=32)


class AgenticCanvasSceneV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[AGENTIC_CANVAS_SCENE_VERSION]
    objective: str = Field(min_length=1, max_length=500)
    subject_key: str = Field(min_length=1, max_length=64)
    blocks: list[AgenticCanvasBlockV1] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_block_ids(self) -> "AgenticCanvasSceneV1":
        if len({block.block_id for block in self.blocks}) != len(self.blocks):
            raise ValueError("Agentic Canvas block identifiers must be unique")
        return self


class AgenticCanvasActionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[AGENTIC_CANVAS_ACTION_VERSION]
    action: Literal["FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT"]
    block_id: str = Field(min_length=1, max_length=64)
    element_id: str | None = Field(default=None, min_length=1, max_length=64)
    from_value: str | None = Field(default=None, max_length=240)
    to_value: str | None = Field(default=None, max_length=240)


def build_agentic_tutor_projection(*, objective: str, subject_key: str, scene_status: str, blocks: list[dict[str, object]], actions: list[AgenticCanvasActionV1]) -> dict[str, object]:
    """Return only durable semantic state; browser/layout details never enter Tutor context."""
    parsed_blocks = [AgenticCanvasBlockV1.model_validate(block) for block in blocks]
    return {
        "version": "agentic-canvas-tutor-projection-v1",
        "scene_objective": objective,
        "subject": subject_key,
        "scene_status": scene_status,
        "blocks": [
            {"block_id": block.block_id, "type": block.type, "meaning": block.meaning,
             "elements": [element.model_dump() for element in block.elements]}
            for block in parsed_blocks
        ],
        "current_focus": None,
        "recent_student_actions": [
            {"action": action.action, "block_id": action.block_id, "element_id": action.element_id,
             "from": action.from_value, "to": action.to_value}
            for action in actions
        ],
    }
