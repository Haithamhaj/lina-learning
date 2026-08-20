"""Prepare the local-only Grade 5 Eureka Math sandbox source and structural run.

The PDF is downloaded to ``.local/eureka`` (which is Git-ignored) and is never
copied into the repository. It is development/test curriculum content only.
"""

from __future__ import annotations

from pathlib import Path
import sys
from urllib.request import urlretrieve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from services.content.ingestion import ingest_source_document
from services.content.processing import process_structural_document
from services.content.semantics import extract_educational_semantics
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StaticModelProvider
from services.platform.db.connection import get_engine
from services.platform.db.models import ModelTask, Student, User
from services.platform.storage import LocalObjectStorage

URL = "https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Student_Workbook/G5_StudentWorkbook/EM_G5_M1_StudentWorkbook.pdf"
PDF_PATH = Path(".local/eureka/EM_G5_M1_StudentWorkbook.pdf")
SANDBOX_SUBJECT = "sandbox-eureka-grade5"


def main() -> None:
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
        if run.status == "COMPLETED":
            gateway = ModelGateway(
                session,
                routes={ModelTask.CURRICULUM_SEMANTICS: ModelRoute("local-demo", "deterministic-semantic-v1")},
                providers={"local-demo": StaticModelProvider(ModelResult(output={}))},
            )
            nodes = extract_educational_semantics(session, document=document, gateway=gateway)
        else:
            nodes = []
        session.commit()
        print(f"Sandbox student: {student.id}")
        print(f"Source document: {document.id} ({document.status})")
        print(f"Docling run: {run.id} ({run.status})")
        print(f"Curriculum nodes: {len(nodes)}")
        if run.failure_detail:
            print(f"Failure: {run.failure_detail}")


if __name__ == "__main__":
    main()
