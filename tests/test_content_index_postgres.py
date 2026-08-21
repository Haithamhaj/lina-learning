"""PostgreSQL contracts for TASK-013 indexed content blocks."""
from __future__ import annotations
import os
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from services.content.indexing import build_content_index, lexical_candidates, vector_candidates
from services.content.repository import create_content_document, create_processing_run, create_semantic_items, create_semantic_processing_run, create_structural_items
from services.content.semantic_contract import SemanticExtractionItem
from services.content.structural_contract import NormalizedStructuralItem
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StaticModelProvider
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ContentIndexRun, ContentSemanticItem, IndexedContentBlock, IndexedContentBlockSource, ModelTask, Student, User


def test_task013_index_contract_is_available() -> None:
    assert build_content_index is not None
    assert ContentIndexRun.__tablename__ == "content_index_runs"
    assert IndexedContentBlock.__tablename__ == "indexed_content_blocks"

def test_task013_indexing_has_no_python_all_block_ranking_path() -> None:
    source = Path("services/content/indexing.py").read_text()
    assert "sorted(" not in source
    assert "deterministic_embedding" not in source

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL required")

@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as c: c.execute(text("TRUNCATE indexed_content_block_sources, indexed_content_blocks, content_index_runs, content_semantic_item_sources, content_semantic_items, content_semantic_processing_runs, document_structural_items, content_processing_runs, content_documents CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False); engine.dispose()

def _setup(session: Session, source_text="Place value explains how digits change when multiplying decimals by ten."):
    user=User(identity_provider="fixture", external_subject=uuid4().hex); session.add(user); session.flush(); student=Student(user_id=user.id, display_name="fixture"); session.add(student); session.flush()
    doc=create_content_document(session, student_id=student.id, grade_level=5, subject="MATH", original_storage_key="fixture", original_checksum=uuid4().hex*2, filename="fixture.pdf", content_type="application/pdf")
    structural=create_processing_run(session, document_id=doc.id, kind="STRUCTURAL", processor_version="v1"); structural.status="COMPLETED"
    rows=create_structural_items(session, document_id=doc.id, processing_run_id=structural.id, items=[NormalizedStructuralItem(item_key="source",parent_item_key=None,sibling_order=0,reading_order=0,hierarchy_depth=0,item_type="text",text=source_text,caption_text=None,caption_item_keys=(),heading_level=1,page_number=2,source_ref="fixture#page=2",provenance={},attributes={})])
    sem=create_semantic_processing_run(session, document_id=doc.id, structural_processing_run_id=structural.id, semantic_schema_version="v1", prompt_version="v1", model_route_version="fixture", provider="fixture", model="fixture", settings_version="v1", settings_metadata={}); sem.status="COMPLETED"
    item=SemanticExtractionItem(semantic_key="place-value",semantic_type="CONCEPT",title="Place Value",description="Decimal place value",normalized_concept_key="place-value",parent_semantic_key=None,structural_item_keys=["source"],sibling_order=0,metadata={})
    create_semantic_items(session, document_id=doc.id, semantic_processing_run_id=sem.id, items=[item], structural_items_by_key={"source":rows[0]})
    return doc,sem

def _gateway(session: Session, vector=None):
    class Provider:
        def execute(self, route, payload):
            del route
            return ModelResult(output={"embeddings":[vector or [0.01]*1536 for _ in payload["input"]]})
    return ModelGateway(session, routes={ModelTask.EMBEDDING: ModelRoute("fixture","text-embedding-3-small")}, providers={"fixture":Provider()})

def test_index_persists_metadata_lineage_and_db_queries(factory):
    with factory.begin() as session:
        doc,sem=_setup(session); run=build_content_index(session,document=doc,semantic_run=sem,gateway=_gateway(session)); block=session.query(IndexedContentBlock).one()
        source=session.query(IndexedContentBlockSource).one(); lexical=lexical_candidates(session,index_run_id=run.id,query="decimal place",grade_level=5,subject="MATH",concept_key="place-value")
        vector=vector_candidates(session,index_run_id=run.id,embedding=[0.01]*1536,grade_level=5,subject="MATH",concept_key="place-value")
    assert run.status=="COMPLETED" and len(block.embedding)==1536
    assert block.grade_level==5 and block.subject=="MATH" and block.concept_key=="place-value"
    assert source.block_id==block.id and source.page_number==2 and source.source_ref=="fixture#page=2"
    assert lexical[0].id==block.id and vector[0].id==block.id

def test_index_is_idempotent_and_preserves_prior_on_new_failure(factory):
    with factory.begin() as session:
        doc,sem=_setup(session); first=build_content_index(session,document=doc,semantic_run=sem,gateway=_gateway(session)); same=build_content_index(session,document=doc,semantic_run=sem,gateway=_gateway(session)); failed=build_content_index(session,document=doc,semantic_run=sem,gateway=_gateway(session, [0.1]*8),settings_version="v2")
        retained=session.query(IndexedContentBlock).filter_by(index_run_id=first.id).count()
    assert same.id==first.id and failed.status=="FAILED" and retained==1

def test_oversized_semantic_content_is_refined_not_skipped(factory):
    with factory.begin() as session:
        doc,sem=_setup(session, "x"*4500); run=build_content_index(session,document=doc,semantic_run=sem,gateway=_gateway(session))
        blocks=session.query(IndexedContentBlock).filter_by(index_run_id=run.id).all()
    assert len(blocks)==3 and all(block.text for block in blocks)
