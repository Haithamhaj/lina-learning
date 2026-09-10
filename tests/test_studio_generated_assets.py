from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from services.platform.db import models as m
from services.platform.storage import (
    LocalObjectStorage,
    ObjectNotFoundError,
    StorageIntegrityError,
)


def _png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(output, format="PNG")
    return output.getvalue()


def _service():
    return importlib.import_module("services.studio.generated_assets")


def _run() -> m.StudioCanvasSpecialistRun:
    student_id = uuid4()
    session_id = uuid4()
    runtime_id = uuid4()
    return m.StudioCanvasSpecialistRun(
        id=uuid4(),
        studio_runtime_id=runtime_id,
        student_id=student_id,
        learning_session_id=session_id,
        source_message_id=uuid4(),
        base_scene_version=0,
        subject_key="CANVAS",
        capability_profile_version="agentic-canvas-v1",
        output_schema_version="agentic-canvas-scene-v1",
    )


def test_generated_asset_schema_keeps_only_owned_immutable_metadata() -> None:
    """Adding bytes, provider URLs, or temporary handles to the row is a privacy bug."""

    model = getattr(m, "StudioGeneratedAsset", None)
    assert model is not None
    assert set(model.__table__.columns.keys()) == {
        "id",
        "student_id",
        "learning_session_id",
        "studio_runtime_id",
        "source_run_id",
        "kind",
        "content_type",
        "size_bytes",
        "checksum_sha256",
        "storage_key",
        "created_at",
    }
    assert not ({"content", "base64", "provider_url", "temporary_handle"} & set(model.__table__.columns.keys()))


def test_generated_image_validation_preserves_bytes_and_rejects_non_images() -> None:
    """Persisting arbitrary hosted-tool output as an image would bypass the asset boundary."""

    service = _service()
    content = _png()
    image = service.validate_generated_image_output(content=content, content_type="image/png")
    assert image.content == content
    assert image.content_type == "image/png"
    assert image.size_bytes == len(content)
    assert image.checksum_sha256 == "af9cb484e25836824f7bf5adede1e0ce33aea0abaae1e8978b5ec30e99ca27f1"

    with pytest.raises(service.GeneratedAssetValidationError, match="supported image"):
        service.validate_generated_image_output(content=b"<svg><script/></svg>", content_type="image/svg+xml")
    with pytest.raises(service.GeneratedAssetValidationError, match="invalid image"):
        service.validate_generated_image_output(content=b"not-an-image", content_type="image/png")


def test_persisted_image_uses_owned_storage_and_never_records_temporary_handle_or_url(tmp_path: Path) -> None:
    """A provider handle must resolve to an opaque project-owned asset identifier."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _Session:
        def __init__(self) -> None:
            self.added = None

        def add(self, value: object) -> None:
            self.added = value

        def flush(self, values: object | None = None) -> None:
            return None

    database = _Session()
    resolution = service.adopt_generated_image(
        database,
        storage=storage,
        run=run,
        temporary_handle="hosted-image-1",
        content=_png(),
        content_type="image/png",
    )

    assert resolution.temporary_handle == "hosted-image-1"
    assert resolution.asset_id == resolution.asset.id
    assert database.added is resolution.asset
    assert "hosted-image-1" not in resolution.asset.storage_key
    assert storage.get(resolution.asset.storage_key).content == _png()
    assert all(
        "url" not in column.name.lower()
        for column in resolution.asset.__table__.columns
    )

    draft = {
        "version": "agentic-canvas-scene-v1",
        "objective": "Show the observation",
        "subject_key": "SCIENCE",
        "blocks": [
            {
                "block_id": "image-one",
                "type": "IMAGE",
                "meaning": "A generated observation diagram",
                "title": "Observation",
                "accessibility": {"text_equivalent": "A safe observation diagram", "aria_label": None},
                "allowed_actions": ["FOCUS"],
                "elements": [],
                "temporary_image_handle": "hosted-image-1",
                "provider_url": "https://provider.invalid/temporary",
            }
        ],
    }
    resolved = service.resolve_generated_image_handles(draft, resolutions=[resolution])
    block = resolved["blocks"][0]
    assert block["studio_generated_asset_id"] == str(resolution.asset_id)
    assert "temporary_image_handle" not in block
    assert "provider_url" not in block
    assert "provider.invalid" not in repr(resolved)


def test_worker_adopts_hosted_image_bytes_before_building_the_durable_scene(tmp_path: Path) -> None:
    from services.studio.agent.orchestrator import HostedGeneratedImage
    from services.studio.agentic_canvas import AgenticCanvasSceneV1
    from services.studio.canvas_brief import CanvasBriefV1
    from workers.agentic_canvas_handlers import _adopt_hosted_images

    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _Session:
        def add(self, value: object) -> None:
            self.added = value

        def flush(self, values: object | None = None) -> None:
            return None

    brief = CanvasBriefV1.model_validate({
        "version": "canvas-brief-v1",
        "subject_key": "SCIENCE",
        "objective": "Observe the water cycle.",
        "student_request": "Show the water cycle.",
        "requested_representation": "A simple water-cycle illustration.",
        "facts": ["Water changes state."],
        "relations": [],
        "quantities": [],
        "desired_student_action": None,
        "must_not_imply": [],
        "source_references": [],
        "locale": "en",
        "direction": "ltr",
    })
    scene = AgenticCanvasSceneV1.model_validate({
        "version": "agentic-canvas-scene-v1",
        "objective": "Observe the water cycle.",
        "subject_key": "SCIENCE",
        "blocks": [{
            "block_id": "cycle",
            "type": "DIAGRAM",
            "meaning": "Water moves through a repeating cycle.",
            "title": "Water cycle",
            "accessibility": {"text_equivalent": "A water-cycle diagram.", "aria_label": None},
            "allowed_actions": ["FOCUS"],
            "elements": [],
            "topology": "CYCLE",
            "layout": "RADIAL",
            "nodes": [],
            "edges": [],
        }],
    })

    adopted = _adopt_hosted_images(
        _Session(),
        storage=storage,
        run=run,
        brief=brief,
        scene=scene,
        generated_images=(HostedGeneratedImage(
            temporary_handle="image-call-1",
            content=_png(),
        ),),
    )

    image_block = adopted.blocks[-1]
    assert image_block.type == "IMAGE"
    assert image_block.studio_generated_asset_id
    assert "image-call-1" not in adopted.model_dump_json()
    assert "base64" not in adopted.model_dump_json()
    assert "provider" not in adopted.model_dump_json()


def test_database_failure_deletes_adopted_bytes(tmp_path: Path) -> None:
    """A failed row insert must not leave an ownerless object behind."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _FailingSession:
        def add(self, _: object) -> None:
            return None

        def flush(self, _: object | None = None) -> None:
            raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.adopt_generated_image(
            _FailingSession(),
            storage=storage,
            run=run,
            temporary_handle="hosted-image-2",
            content=_png(),
            content_type="image/png",
        )

    owned_root = tmp_path / "objects" / "studio-generated-assets"
    assert not owned_root.exists() or not any(path.is_file() for path in owned_root.glob("**/*"))


def test_outer_transaction_rollback_deletes_flushed_asset_bytes(tmp_path: Path) -> None:
    """A later transaction rollback must compensate after adoption already returned."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _NoDatabaseSession(Session):
        def flush(self, objects: object | None = None) -> None:
            # Keep Session transaction events real while avoiding a database in
            # this focused object-lifecycle contract.
            for value in list(self.new):
                self.expunge(value)

    database = _NoDatabaseSession()
    resolution = service.adopt_generated_image(
        database,
        storage=storage,
        run=run,
        temporary_handle="hosted-image-rollback",
        content=_png(),
        content_type="image/png",
    )
    storage.head(resolution.asset.storage_key)

    database.rollback()

    owned_root = tmp_path / "objects" / "studio-generated-assets"
    assert not owned_root.exists() or not any(path.is_file() for path in owned_root.glob("**/*"))


def test_successful_outer_commit_cancels_asset_compensation(tmp_path: Path) -> None:
    """A later Session close/rollback must not delete bytes whose row committed."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _NoDatabaseSession(Session):
        def flush(self, objects: object | None = None) -> None:
            for value in list(self.new):
                self.expunge(value)

    database = _NoDatabaseSession()
    resolution = service.adopt_generated_image(
        database,
        storage=storage,
        run=run,
        temporary_handle="hosted-image-commit",
        content=_png(),
        content_type="image/png",
    )

    database.commit()
    database.close()

    assert storage.get(resolution.asset.storage_key).content == _png()


def test_nested_savepoint_rollback_deletes_only_its_generated_asset(tmp_path: Path) -> None:
    """Outer commit must not orphan bytes whose asset row died in a savepoint."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _NoDatabaseSession(Session):
        def flush(self, objects: object | None = None) -> None:
            for value in list(self.new):
                self.expunge(value)

    database = _NoDatabaseSession()
    database.begin()
    root_resolution = service.adopt_generated_image(
        database,
        storage=storage,
        run=run,
        temporary_handle="hosted-image-root-commit",
        content=_png(),
        content_type="image/png",
    )
    savepoint = database.begin_nested()
    resolution = service.adopt_generated_image(
        database,
        storage=storage,
        run=run,
        temporary_handle="hosted-image-savepoint-rollback",
        content=_png(),
        content_type="image/png",
    )
    storage.head(resolution.asset.storage_key)

    savepoint.rollback()
    database.commit()

    assert storage.get(root_resolution.asset.storage_key).content == _png()
    with pytest.raises(ObjectNotFoundError):
        storage.head(resolution.asset.storage_key)


def test_nested_savepoint_commit_remains_pending_until_outer_outcome(tmp_path: Path) -> None:
    """Savepoint success alone cannot cancel compensation before outer rollback."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _NoDatabaseSession(Session):
        def flush(self, objects: object | None = None) -> None:
            for value in list(self.new):
                self.expunge(value)

    database = _NoDatabaseSession()
    database.begin()
    savepoint = database.begin_nested()
    resolution = service.adopt_generated_image(
        database,
        storage=storage,
        run=run,
        temporary_handle="hosted-image-savepoint-commit",
        content=_png(),
        content_type="image/png",
    )

    savepoint.commit()
    storage.head(resolution.asset.storage_key)
    database.rollback()

    owned_root = tmp_path / "objects" / "studio-generated-assets"
    assert not owned_root.exists() or not any(path.is_file() for path in owned_root.glob("**/*"))


def test_private_read_rechecks_immutable_storage_metadata(tmp_path: Path) -> None:
    """Serving bytes with drifted metadata would break durable asset lineage."""

    service = _service()
    storage = LocalObjectStorage(tmp_path / "objects", signing_secret="fixture")
    run = _run()

    class _Session:
        def add(self, _: object) -> None:
            return None

        def flush(self, _: object | None = None) -> None:
            return None

    asset = service.adopt_generated_image(
        _Session(),
        storage=storage,
        run=run,
        temporary_handle="hosted-image-3",
        content=_png(),
        content_type="image/png",
    ).asset
    assert service.read_generated_asset(storage=storage, asset=asset).content == _png()

    asset.checksum_sha256 = "0" * 64
    with pytest.raises(StorageIntegrityError, match="durable lineage"):
        service.read_generated_asset(storage=storage, asset=asset)
