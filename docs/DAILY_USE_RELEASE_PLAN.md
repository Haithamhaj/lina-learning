# Lina Personal Learning System — Daily-Use Release 1

**Status:** Product Owner approved on 2026-08-31  
**Purpose:** Governing implementation addendum for the launch-first transition from accepted core architecture to a reliable private Daily-Use Lina product.  
**Authority:** This addendum supplements `PROJECT_REFERENCE.md` and `IMPLEMENTATION_PLAN.md` for the approved Daily-Use Release 1 sequence. It does not replace Learning Intelligence semantics, Child Safety policy, or historical implementation records. Current executable task authority is `project-state/PROJECT_STATE.md` + `project-state/DAILY_USE_RELEASE_TASKS.md`.

---

# 1. Release Objective

Finish the smallest coherent product Lina can use naturally now that school has started, while preserving the accepted Learning Intelligence core and avoiding premature expansion.

The release objective is not feature completeness. It is:

```text
reliable private environment
+ clean real-use database
+ authenticated Lina/Parent identities
+ real Model Gateway routes
+ Worker-backed intelligence lifecycle
+ Personal Facts from Day 1
+ child-appropriate Daily Student frontend
+ Voice → STT
+ Student photo/Vision
+ original-image annotation
→ Lina starts real recurring use
```

RAG redesign, broad Parent Insights, advanced ML/clustering, optional image generation, Science production, and a large Artifact Engine do not block Release 1.

---

# 2. Product Decisions Added by This Release

## 2.1 Clean Real-Use Baseline

The existing historical database and prior interaction data are experimental/test material. They are not the longitudinal real-use baseline to preserve.

Real Lina use starts on a **fresh database migrated from zero on the current accepted schema**. Historical limited Real-Lina use remains true as product history but is not imported as production personalization history.

## 2.2 Personal Facts

Lina Learning adds a separate **Personal Facts** context layer.

It answers:

> **What durable factual things has the Student told the system about herself or her world?**

Examples include self-asserted interests, likes/dislikes, relationships/names, pets, activities, goals, preferences, and other durable facts worth remembering.

Personal Facts are distinct from:

- Student Core Profile,
- Conversation Context,
- Learning Intelligence,
- Evidence,
- Current State / Patterns,
- Safety classification,
- curriculum/RAG grounding.

### Source authority

Personal Facts come from the Student's own assertions/interactions. Parent-supplied claims do not automatically become the Student's Personal Facts. A Personal Fact represents what the Student has asserted for personalization continuity; it is not required to be externally verified civil/objective truth.

### Prohibited interpretation

Do not convert Personal Facts into:

- personality conclusions,
- psychological diagnosis,
- intelligence labels,
- learning-style labels,
- global motivational judgments,
- Learning Evidence.

### Temporal behavior

Facts may be supported repeatedly, contradicted, invalidated, or superseded. Preserve source-message lineage and time evolution so current context can change without erasing history.

### Parent visibility

Parent may inspect stored Personal Facts. The current product does not require a separate hidden Student-facts store.

### Future insight exploration

A later Parent insight layer may analyze the intersection of Personal Facts and Learning Intelligence after sufficient real data exists. That future analysis is intentionally data-driven and may use descriptive analytics, LLM analysis, clustering, or ML only when justified. Derived Parent insights do not write themselves back as Personal Facts or Learning Intelligence truth.

---

# 3. Model / Infrastructure Direction

## 3.1 Preserve Existing Core

Use the current modular monolith:

```text
Next.js Web
   ↓
FastAPI Backend
   ├── Tutor
   ├── Personal Facts
   ├── Learning Intelligence
   ├── Content / Retrieval
   ├── Model Gateway
   └── Platform
   ↓
PostgreSQL + pgvector
Object Storage
DB-backed Worker
```

Do not add Redis/Celery, microservices, graph infrastructure, dedicated vector databases, or generic agent chains without measured need.

## 3.2 Model Gateway

Application domains continue to request AI by task, not provider SDK.

Release 1 may promote task routes such as:

- `tutor`
- `segment_evidence`
- `embedding`
- `personal_fact_extraction`
- `speech_to_text`
- `vision_student_work`

OpenAI is the current practical provider candidate behind the existing gateway. Provider/model remains replaceable architecture.

## 3.3 Authentication

Keep Clerk unless a concrete current blocker is reproduced. Do not build a second account/password system.

## 3.4 Runtime Composition

A valid Daily-Use runtime must operate current versions of:

```text
Web + API + Worker + persistent PostgreSQL + Clerk + real Model Gateway + private durable storage
```

Replit may be the first private daily host after the composition is proven. Replit is not product architecture, and the historical Phase-0 Replit app is not the source baseline.

---

# 4. Retrieval / RAG Direction

The current native retrieval stack remains Release-1 baseline:

```text
Docling structure
→ project retrieval blocks
→ metadata filtering
→ lexical retrieval
+ pgvector retrieval
→ project ranking / RRF / expansion
→ bounded provenance-rich context
```

Do not replace it before launch by assumption.

After real use begins, run a bounded RAG evaluation using Lina's actual Grade-5 questions/sources. When practical compare:

- current native Docling + PostgreSQL/pgvector,
- official LlamaIndex + Docling integration,
- OpenAI retrieval/file-search capability.

Evaluate retrieval correctness, page/source provenance, Arabic/English behavior, latency, cost, custom-code/dependency burden, filtering/control, and rebuildability. Change only if measured evidence shows a material advantage behind the current Retrieval boundary.

---

# 5. Daily Student Frontend

Frontend is a Release-1 product capability, not post-launch cosmetic polish.

Target:

> **playful + intelligent + polished + personal**, suitable for roughly age 10 — not preschool and not a corporate chatbot.

## 5.1 Reuse evaluation

Before broad frontend changes, evaluate the approved sources selectively:

- shadcn/ui — functional baseline;
- existing assistant-ui decision / custom-runtime fit if revisited by concrete need;
- Motion / Motion Primitives;
- ThreeUI / Three.js;
- Magic UI;
- React Bits;
- 21st.dev;
- Aceternity UI;
- Cult UI.

Each relevant candidate receives `ADOPT / PARTIAL ADOPT / VISUAL REFERENCE / REJECT`.

Do not stack libraries for novelty. Build one coherent Lina design system.

## 5.2 ThreeUI / Three.js

Use selectively when a 3D/animated visual materially improves delight, orientation, or a learning moment without harming performance/readability. It is not the application architecture.

## 5.3 Daily experience requirements

The Student experience should include a coherent Home/Tutor entry, polished conversation/composer, suggested actions/guided checks, thinking/loading/error/retry states, bilingual RTL/LTR handling, and responsive browser behavior. Voice/photo controls may be staged visually before they become active in their later tasks.

---

# 6. Voice

Release-1 Voice uses the simplest approved path:

```text
record short audio
→ speech-to-text
→ transcript
→ normal Tutor pipeline
```

Requirements:

- Arabic/English/mixed transcription where supported;
- transcript visible before/while sending as the UX requires;
- normal Student message ownership, Safety, persistence, and Tutor context apply;
- raw audio is not retained after successful STT under current policy.

Speech-to-speech/realtime conversational audio is not required for Release 1. Promote later only if real use shows clear value.

---

# 7. Student Images / Vision

Lina may photograph/upload homework, handwritten work, drawings, diagrams, or textbook/worksheet pages.

The original asset remains source authority.

```text
Original Student Image
→ Vision interpretation
→ ambiguous? ask Lina simply
→ Tutor continues
```

Vision interpretation is derived and never replaces original work.

---

# 8. Visual Output — Renderer First

Teaching visuals are **renderer-first**, not image-generation-first.

Primary stack:

- React/SVG
- Motion
- JSXGraph
- React Konva
- MathLive

Optional later by concrete need:

- Rough.js
- Recharts
- p5.js
- React Flow

Use reusable/typed visual representations for Math/Science correctness, interaction, low cost, and control.

OpenAI or other image generation is optional/deferred and may be used later for illustrative images when it adds value. It is not the default teaching renderer.

---

# 9. Student Image Annotation

For photographed work, the default visual feedback path is:

```text
Original Image
→ understand work
→ generate annotation on a derived copy
   (circles / arrows / highlights / ✓ / ✕ / short notes)
→ show annotated derived artifact
```

The original object remains unchanged.

When annotation is insufficient:

```text
Original Image
→ interpretation
→ clean React/SVG/interactive reconstruction
```

The reconstruction is a teaching artifact, not evidence of what Lina originally produced.

---

# 10. Launch Sequence

The approved launch order is governed by `project-state/DAILY_USE_RELEASE_TASKS.md`:

```text
1. RL-01A — Accepted Runtime Alignment
2. RL-01B — Fresh DB + Runtime Composition
3. RL-01C — Clerk + OpenAI Operational Verification
4. RL-01D — Controlled Full Intelligence Loop
5. TASK-027A — Student Core Profile
6. PF-01 — Personal Facts Contract
7. PF-02 — Personal Facts Extraction/Reconciliation
8. PF-03 — Relevant Facts in Tutor Context
9. FE-01 — Lina Visual System & Reuse Decision
10. FE-02 — Daily Student Experience
11. TASK-032 — Voice / STT
12. TASK-033 — Vision / Student Work
13. TASK-034 — Original-Image Annotation
14. DEPLOY-01 — Private Daily Environment
15. LINA-R1 — Clean Real-Use Baseline
```

Only the explicitly `READY` task may execute.

---

# 11. Post-Launch Deliberate Deferrals

These do not block Lina starting real use:

- RAG framework replacement;
- large generic Artifact Engine / Learning Canvas expansion;
- optional AI image generation;
- Science production expansion;
- Parent Facts × Learning insights;
- talent/potential detection logic;
- advanced ML/clustering;
- graph database / Graphiti;
- broader Parent dashboard expansion;
- Grade transition production.

Real use should determine which one deserves promotion next.

---

# 12. Release Principle

> **Finish one reliable product Lina can use now. Capture clean durable data from Day 1. Expand from real evidence instead of delaying use until every future capability is complete.**
