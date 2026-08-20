# Development Sandbox Demo

The browser demo uses a separate **Sandbox/Test Learner**, not Lina. Its local
Grade 5 Math source is the official [Eureka Math Grade 5 Module 1 Student
Workbook](https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Student_Workbook/G5_StudentWorkbook/EM_G5_M1_StudentWorkbook.pdf).
The workbook is development/test curriculum content only. The setup script
downloads it into `.local/eureka/`, which Git ignores; do not commit or
redistribute the PDF.

With PostgreSQL running and `DATABASE_URL` set:

```bash
uv run --with-requirements apps/api/requirements.txt python scripts/setup_eureka_demo.py
uv run --with-requirements apps/api/requirements.txt uvicorn apps.api.main:app --port 8000
```

In a second terminal:

```bash
cd apps/web
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api npm run dev
```

Open `http://localhost:5000/demo`. Try the initial place-value attempt, choose
**Close & consolidate**, open a later session, and ask another multiplication
question. The Tutor shows the selected compact intelligence note only when it
is relevant. The right-hand development inspector exposes source documents,
Candidate Events, Events/Evidence, Current State, Patterns, Cards, and derived
decision views. **Rebuild intelligence** creates a new derived run from raw
messages/candidates; it does not replace originals.

This proves the sandbox loop only. It does not validate real Lina behavior or
replace later validation with Lina's chosen school book.
