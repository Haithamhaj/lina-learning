"""Prepare the local-only Grade 5 Eureka Math sandbox source and structural run.

The PDF is downloaded to ``.local/eureka`` (which is Git-ignored) and is never
copied into the repository. It is development/test curriculum content only.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from urllib.request import urlretrieve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from services.content.ingestion import ingest_source_document
from services.content.processing import process_structural_document
from services.content.semantics import extract_educational_semantics
from services.model_gateway.factory import create_curriculum_semantics_gateway
from services.platform.db.connection import get_engine
from services.platform.db.models import ContentSemanticItem, Student, User
from services.platform.storage import LocalObjectStorage

URL = "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Student_Workbook/G5_StudentWorkbook/EM_G5_M1_StudentWorkbook.pdf"
PDF_PATH = Path(".local/eureka/EM_G5_M1_StudentWorkbook.pdf")
SANDBOX_SUBJECT = "sandbox-eureka-grade5"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract-semantics",
        action="store_true",
        help="Run the configured Model Gateway semantic route after structural processing.",
    )
    args = parser.parse_args()
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PDF_PATH.exists():
        print("Downloading the official Eureka Math Grade 5 Module 1 workbook to local cache…")
        urlretrieve(URL, PDF_PATH)
    storage = LocalObjectStorage(Path(".local/storage"), signing_secret="development-demo")
    with Session(get_engine()) as session:
        user = session.query(User).filter_by(identity_provider="development-demo", external_subject=SANDBOX_SUBJECT).one_or_none()
        if user is None:
            user = User(identity_provider="development-demo", external_subject=SANDBOX_SUBJECT, display_name="Sandbox Test Learner")
            session.add(user); session.flush()
            student = Student(user_id=user.id, display_name="Sandbox Test Learner")
            session.add(student); session.flush()
        else:
            student = session.query(Student).filter_by(user_id=user.id).one()
        document = ingest_source_document(session, storage=storage, student_id=student.id, grade_level=5, subject="MATH", filename=PDF_PATH.name, content_type="application/pdf", content=PDF_PATH.read_bytes())
        run = process_structural_document(session, storage=storage, document=document)
        semantic_run = None
        if run.status == "COMPLETED" and args.extract_semantics:
            gateway = create_curriculum_semantics_gateway(session)
            semantic_run = extract_educational_semantics(
                session,
                document=document,
                structural_run=run,
                gateway=gateway,
            )
        session.commit()
        print(f"Sandbox student: {student.id}")
        print(f"Source document: {document.id} ({document.status})")
        print(f"Docling run: {run.id} ({run.status})")
        if semantic_run is not None:
            node_count = session.query(ContentSemanticItem).filter_by(semantic_processing_run_id=semantic_run.id).count()
            print(f"Semantic run: {semantic_run.id} ({semantic_run.status})")
            print(f"Semantic items: {node_count}")
        else:
            print("Semantic extraction not requested; use --extract-semantics with a configured model route.")
        if run.failure_detail:
            print(f"Failure: {run.failure_detail}")


if __name__ == "__main__":
    main()
