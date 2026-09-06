"""Arabic API ownership and historical-source proof through real Gateway composition."""
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import func, select

from test_studio_gateway_composition_postgres import application, prepare_submission, protected_counts
from services.platform.db import models as m
from services.platform.auth import AuthenticatedPrincipal, UserRole
from services.platform.auth.clerk import get_current_principal
from services.tutor.runtime import LocalTutorProvider


def test_arabic_original_submission_survives_later_edit_and_ownership_denials(application, monkeypatch):
    from apps.api.main import app
    client, factory = application
    runtime_id, session_id, interaction_id, operation = prepare_submission(client, factory, "ARABIC")
    source_order = list(operation["payload"]["token_ids"])
    path = f"/api/v1/student/studio/{runtime_id}"
    with factory() as session:
        before_protected = protected_counts(session)
        assert session.scalar(select(func.count()).select_from(m.AIExecution)) == 0
        before_events = session.scalar(select(func.count()).select_from(m.StudioEvent))
    edit = {**operation, "action_key": "REORDER_TOKEN", "payload": {"token_id": source_order[0], "from_index": 0, "to_index": 2}, "base_scene_version": 3, "idempotency_key": "later-record-only"}
    response = client.post(path + "/operations", json=edit)
    assert response.status_code == 200
    assert response.json()["student_interaction_id"] is None
    current_order = source_order[1:] + source_order[:1]
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(m.StudioStudentInteraction)) == 1
        assert session.scalar(select(func.count()).select_from(m.AIExecution)) == 0
        assert session.scalar(select(func.count()).select_from(m.LearningMessage)) == 0
        assert session.scalar(select(func.count()).select_from(m.StudioEvent)) == before_events + 1
    snapshot = client.get(path + "/snapshot").json()
    with factory.begin() as session:
        user = m.User(identity_provider="clerk", external_subject="arabic-other", role="STUDENT")
        session.add(user); session.flush()
        session.add(m.Student(user_id=user.id, display_name="Other technical Student"))
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(subject="arabic-other", role=UserRole.STUDENT)
    assert client.get(path + "/snapshot").status_code == 404
    assert client.post(path + "/operations", json=edit).status_code == 404
    assert client.post(path + f"/interactions/{interaction_id}/turn/stream").status_code == 404
    assert client.get(f"/api/v1/student/studio/{uuid4()}/snapshot").status_code == 404
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(subject="gateway-canvas", role=UserRole.STUDENT)
    assert client.get(path + "/snapshot").json() == snapshot
    # Replay returns the existing effect; stale/new malformed requests cannot mutate it.
    assert client.post(path + "/operations", json=edit).json()["replayed"] is True
    assert client.post(path + "/operations", json={**edit,"idempotency_key":"stale-new"}).status_code == 409
    for index, order in enumerate(([], source_order[:2], source_order + ["extra"], [source_order[0]] * 3, ["unknown",*source_order[1:]], source_order)):
        bad = {**operation, "base_scene_version":4,"payload":{"token_ids":order},"idempotency_key":f"malformed-{index}"}
        assert client.post(path + "/operations",json=bad).status_code in (409,422)
    assert client.get(path + "/snapshot").json() == snapshot
    calls = []
    original = LocalTutorProvider.execute
    def observe(self, route, payload):
        calls.append(deepcopy(payload))
        context = payload["studio_interaction_context"]
        assert context["source"]["event"]["action_payload"] == {"token_ids": source_order}
        assert context["source"]["event"]["validation"]["feedback_code"] == "ARABIC_VERB_INITIAL_SENTENCE_NEEDS_REORDERING"
        assert context["source"]["live_subject"]["broad_subject"] == "LANGUAGE_ARTS"
        assert context["workspace"]["state"]["arabic_sentence_ordering_workspace"]["token_ids"] == current_order
        assert payload["studio_workspace_context"]["snapshot"]["state"]["arabic_sentence_ordering_workspace"]["token_ids"] == current_order
        return original(self, route, payload)
    monkeypatch.setattr(LocalTutorProvider, "execute", observe)
    response = client.post(path + f"/interactions/{interaction_id}/turn/stream")
    assert response.status_code == 200 and "event: turn" in response.text
    assert len(calls) == 1
    with factory() as session:
        interaction = session.get(m.StudioStudentInteraction, interaction_id)
        assert interaction.status == "COMPLETED"
        message = session.get(m.LearningMessage, interaction.tutor_message_id)
        assert message.role == "tutor" and message.payload["turn_origin"] == "STUDIO_INTERACTION"
        assert message.payload["student_interaction_id"] == str(interaction_id)
        assert message.ai_execution_id == interaction.ai_execution_id
        assert session.scalar(select(func.count()).select_from(m.LearningMessage)) == 1
        assert session.scalar(select(func.count()).select_from(m.AIExecution)) == 1
        assert protected_counts(session) == before_protected
