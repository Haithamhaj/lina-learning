from __future__ import annotations

from uuid import uuid4

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.models import ModelTask
from services.studio.canvas_brief import CanvasBriefV1
from services.studio.visual_personalization_decision import select_visual_personalization_facts
from services.tutor.runtime import build_tutor_model_payload


class _Session:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        self.rows.append(row)

    def flush(self) -> None:
        return None


class _Provider:
    def __init__(self, answers: dict[str, object] | None = None, *, fails: bool = False) -> None:
        self.answers = answers or {}
        self.fails = fails
        self.payload: dict[str, object] | None = None

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        del route
        self.payload = payload
        if self.fails:
            raise TimeoutError("synthetic")
        return ModelResult(output={"answers": self.answers}, input_tokens=90, output_tokens=0)


def _brief() -> CanvasBriefV1:
    return CanvasBriefV1.model_validate(
        {
            "version": "canvas-brief-v1",
            "subject_key": "MATH",
            "objective": "Compare one half and one third",
            "student_request": "Show it visually",
            "requested_representation": "fraction bars",
            "facts": ["1/2 is greater than 1/3"],
            "relations": [],
            "quantities": [],
            "desired_student_action": "compare the bars",
            "must_not_imply": [],
            "source_references": [],
            "locale": "en",
            "direction": "ltr",
        }
    )


def _gateway(provider: _Provider) -> tuple[ModelGateway, _Session]:
    session = _Session()
    return (
        ModelGateway(
            session,
            routes={ModelTask.CANVAS_VISUAL_PERSONALIZATION: ModelRoute("fixture", "jev")},
            providers={"fixture": provider},
        ),
        session,
    )


def test_visual_fact_selection_is_thresholded_ranked_and_bounded() -> None:
    provider = _Provider(
        {
            "fact_0": {"noul": 0.82},
            "fact_1": {"noul": 0.97},
            "fact_2": {"noul": 0.79},
            "fact_3": {"noul": 0.90},
            "fact_4": {"noul": 0.88},
        }
    )
    gateway, session = _gateway(provider)
    candidates = [
        {"fact_key": f"fact_{index}", "category": "FAVORITE", "display_statement": label}
        for index, label in enumerate(["space", "cats", "football", "oceans", "trains"])
    ]

    decision = select_visual_personalization_facts(
        gateway,
        brief=_brief(),
        candidates=candidates,
        min_probability=0.80,
        policy_version="policy-v1",
        student_id=uuid4(),
        learning_session_id=uuid4(),
        source_message_id=uuid4(),
    )

    assert decision.status == "COMPLETED"
    assert decision.selected_keys == ("fact_1", "fact_3", "fact_4")
    assert decision.selection_payload()["personal_fact_keys"] == ["fact_1", "fact_3", "fact_4"]
    assert len(session.rows) == 1
    assert provider.payload is not None
    assert provider.payload["state"]["candidates"] == candidates
    question = provider.payload["questions"]["fact_0"]
    assert set(question) == {"type", "instructions", "true_when", "false_when"}
    assert "fact_0" in question["instructions"]


def test_visual_fact_provider_failure_safely_selects_no_facts() -> None:
    gateway, session = _gateway(_Provider(fails=True))
    decision = select_visual_personalization_facts(
        gateway,
        brief=_brief(),
        candidates=[{"fact_key": "space", "category": "FAVORITE", "display_statement": "likes space"}],
        min_probability=0.8,
        policy_version="policy-v1",
        student_id=uuid4(),
        learning_session_id=uuid4(),
        source_message_id=uuid4(),
    )

    assert decision.status == "FAILED"
    assert decision.selected_keys == ()
    assert decision.selection_payload()["personal_fact_keys"] == []
    assert len(session.rows) == 1


def test_active_delegation_removes_fact_catalogue_from_luna_context() -> None:
    payload = build_tutor_model_payload(
        question="Show equivalent fractions visually.",
        visual_personalization_catalog=[
            {
                "fact_key": "favorite:space",
                "category": "FAVORITE",
                "display_statement": "Likes space",
            }
        ],
        visual_personalization_delegated=True,
    )

    assert payload["visual_personalization_catalog"] == []
    assert "favorite:space" not in payload["input"]
    assert "selection is delegated to a bounded server decision" in payload["input"]
    assert payload["response_schema"]["name"] == "tutor_turn_v13"
    schema = payload["response_schema"]["schema"]
    assert "canvas_visual_context_selection" not in schema["properties"]
    assert "canvas_visual_context_selection" not in schema["required"]
    assert "canvas_visual_context_selection" not in payload["instructions"]
    assert "canvas_visual_context_selection" not in payload["input"]


def test_off_and_shadow_payload_contract_remains_tutor_turn_v12() -> None:
    payload = build_tutor_model_payload(
        question="Show equivalent fractions visually.",
        visual_personalization_catalog=[
            {
                "fact_key": "favorite:space",
                "category": "FAVORITE",
                "display_statement": "Likes space",
            }
        ],
    )

    assert payload["response_schema"]["name"] == "tutor_turn_v12"
    schema = payload["response_schema"]["schema"]
    assert "canvas_visual_context_selection" in schema["properties"]
    assert "canvas_visual_context_selection" in schema["required"]
    assert "favorite:space" in payload["input"]
