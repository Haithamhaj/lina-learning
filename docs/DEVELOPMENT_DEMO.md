# Development Sandbox Demo

The browser demo uses a separate **Sandbox/Test Learner**, not Lina. Its local
Grade 5 Math source is the official [Eureka Math Grade 5 Module 1 Student
Workbook](https://greatminds.org/hubfs/knowledge/resources/math/EM_Basic_Curriculum_Files/Student_Workbook/G5_StudentWorkbook/EM_G5_M1_StudentWorkbook.pdf).
The workbook is development/test curriculum content only. The setup script
downloads it into `.local/eureka/`, which Git ignores; do not commit or
redistribute the PDF.

With PostgreSQL running, use a database dedicated to this demo. The following
uses the existing local `lina_learning_demo` database; it does not access Lina's
real learner data or another project's database.

```bash
export DATABASE_URL='postgresql+psycopg://lina_task006@127.0.0.1:55433/lina_learning_demo'
uv run --with-requirements apps/api/requirements.txt alembic upgrade head
uv run --with-requirements apps/api/requirements.txt python scripts/setup_eureka_demo.py
```

This creates or reuses the immutable source and the approved Docling structural
run. It intentionally does not make an untracked model call. To generate a
versioned Grade 5 Math semantic derivation after configuring the server-only
Model Gateway route below, run:

```bash
uv run --with-requirements apps/api/requirements.txt \
  python scripts/setup_eureka_demo.py --extract-semantics
```

Semantic extraction uses deterministic reading-order batches of at most 40
TASK-011 structural items. Each request receives its local tree/page/source
context plus only compact previously discovered Unit/Lesson/Concept keys. The
model must explicitly link or mark every item in a batch unclassified; the
backend then validates source links, parent keys, duplicate keys, coverage, and
version identity before persistence. This is distinct from later retrieval and
does not create embeddings or an index.

For the small real-content semantic golden check, first run the structural
verifier into a disposable database, configure the server-only model route, and
then run:

```bash
uv run --with-requirements apps/api/requirements.txt \
  python scripts/verify_eureka_semantic_representation.py \
  --database-url "$DATABASE_URL"
```

The golden set uses the real module cover and first place-value practice region
(pages 1–2). It verifies the Grade 5 Module identity, a lesson-level grouping,
place-value concept, instructional objective, worked example, practice,
figure, and source/page links. It is a bounded semantic-quality check, not a
claim that the entire workbook has completed downstream retrieval validation.

## Real Eureka retrieval golden

Use a **disposable** Lina PostgreSQL database with a completed TASK-011 Eureka
structural run. With the server-only OpenAI Model Gateway configured, prepare
the bounded pages 1–2 semantic/index fixture once, then run the retrieval
golden verifier:

```bash
uv run --with-requirements apps/api/requirements.txt \
  python scripts/prepare_eureka_retrieval_golden.py \
  --database-url "$DATABASE_URL"

uv run --with-requirements apps/api/requirements.txt \
  python scripts/verify_eureka_retrieval.py \
  --database-url "$DATABASE_URL"
```

The retrieval golden verifies seven manually selected question styles against
the persisted real source: terminology, paraphrase, worked example, exercise,
figure, with-current-focus, and without-current-focus. Each case must return
the expected semantic type and page/source provenance. It is a bounded
retrieval-quality check for pages 1–2, not a claim that the entire workbook or
real-Lina behavior has been validated.

Start the API from the repository root. `WEB_ORIGIN` must exactly match the
browser URL, including its host and port, because it is used for both CORS and
Clerk authorized-party validation.

```bash
DATABASE_URL="$DATABASE_URL" WEB_ORIGIN='http://127.0.0.1:5002' \
  uv run --with-requirements apps/api/requirements.txt \
  uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd apps/web
npm ci
NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8000/api' \
  npx next dev -H 127.0.0.1 -p 5002
```

Open `http://127.0.0.1:5002/demo`. Try the initial place-value attempt, choose
**Close & consolidate**, open a later session, and ask another multiplication
question. The Tutor shows the selected compact intelligence note only when it
is relevant. The right-hand development inspector exposes source documents,
Candidate Events, Events/Evidence, Current State, Patterns, Cards, and derived
decision views. **Rebuild intelligence** creates a new derived run from raw
messages/candidates; it does not replace originals.

The development-only `/demo` route can run without a Clerk publishable key: it
does not use Clerk or any real learner identity. All normal authenticated web
surfaces still require a valid development `CLERK_PUBLISHABLE_KEY`. If port
5002 is unavailable, choose another unused port and use that exact origin in
both `WEB_ORIGIN` and the Next command.

## Optional live OpenAI Tutor route

The default `mock` route remains useful for deterministic tests. To exercise
the Sandbox/Test Learner through the Model Gateway with OpenAI, use the
Git-ignored repository-root `.env` file only:

```dotenv
MODEL_PROVIDER=openai
MODEL_NAME=gpt-5.6-luna
MODEL_API_KEY=
```

Do not commit the file or place this value in a `NEXT_PUBLIC_*` variable. Restart
only the API after changing the route. The OpenAI adapter uses the Responses API
with `store: false`; the `ai_executions` ledger records provider, model, token
usage (normal input, cached input/writes when returned, and output), latency, estimated
cost, and success/failure without recording the key.

This proves the sandbox loop only. It does not validate real Lina behavior or
replace later validation with Lina's chosen school book.
