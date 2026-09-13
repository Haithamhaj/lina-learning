"""Deterministic Canvas Agent intelligence assembly; never a second routing call."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from services.studio.canvas_brief import CanvasBriefV1, VisualLearnerContextV1


_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "canvas-agent"
_CORE = ("full-power-routing.md", "visual-composition.md", "tool-selection.md", "custom-visual-runtime.md")
_SPECIALISTS = {
    "math": "math-visualization.md",
    "science": "diagrams-and-processes.md",
    "spatial": "spatial-interaction.md",
    "language": "text-learning.md",
    "image": "image-composition.md",
    "custom": "custom-visual-runtime.md",
    "rtl": "bilingual-layout.md",
    "age": "age-adaptive-visuals.md",
}


@lru_cache(maxsize=16)
def _text(name: str) -> str:
    return (_ROOT / "skills" / name).read_text(encoding="utf-8")


def selected_skill_names(brief: CanvasBriefV1, context: VisualLearnerContextV1) -> tuple[str, ...]:
    """Select compact specialist guidance from already-authorized brief/context only."""
    searchable = " ".join((brief.subject_key, brief.objective, brief.student_request, brief.requested_representation or "", brief.desired_student_action or "", *(fact for fact in brief.facts))).casefold()
    chosen: list[str] = list(_CORE)
    if brief.subject_key.casefold() == "math" or any(token in searchable for token in ("fraction", "decimal", "equation", "graph", "coordinate", "angle", "quantity")):
        chosen.append(_SPECIALISTS["math"])
    if brief.subject_key.casefold() == "science" or any(token in searchable for token in ("process", "cycle", "system", "mechanism", "force", "light", "shadow", "water")):
        chosen.append(_SPECIALISTS["science"])
    if any(token in searchable for token in ("move", "drag", "place", "position", "spatial", "contain")):
        chosen.append(_SPECIALISTS["spatial"])
    if any(token in searchable for token in ("continuous", "coupled", "simulation", "dynamic dependency", "updates together")):
        chosen.append(_SPECIALISTS["custom"])
    if brief.subject_key.casefold() in {"arabic", "english"} or any(token in searchable for token in ("sentence", "word", "phrase", "order", "grammar")):
        chosen.append(_SPECIALISTS["language"])
    if any(token in searchable for token in ("illustration", "organism", "animal", "plant", "habitat", "anatomy")):
        chosen.append(_SPECIALISTS["image"])
    if brief.direction == "rtl" or brief.locale.casefold().startswith("ar"):
        chosen.append(_SPECIALISTS["rtl"])
    if context.core_profile.age_years is not None or context.core_profile.grade_level is not None:
        chosen.append(_SPECIALISTS["age"])
    return tuple(dict.fromkeys(chosen))


def assemble_canvas_intelligence(brief: CanvasBriefV1, context: VisualLearnerContextV1) -> str:
    """Return the always-loaded core plus at most relevant deterministic specialists."""
    return "\n\n".join(_text(name) for name in selected_skill_names(brief, context))
