# Lina Personal Learning System — Project State

## Current goal

Move from accepted architecture and completed current-reality audit into the **Daily-Use Lina Release 1** execution sequence approved by the Product Owner on 2026-08-31.

`DOC-SYNC-01 — Product Truth & Governing Documentation Synchronization` is **DONE / ACCEPTED**.

`RL-01 — Real-Use Environment & Integrated Intelligence Loop Verification` has completed its **CURRENT REALITY AUDIT** stage. The audit verified that the current architecture is implemented, while the actual operational environment is not yet aligned as one current revision/runtime: the live historical database/runtime are older than the accepted code, and the Worker is not part of the standard running composition.

The Product Owner clarified that the existing historical database is **experimental/test data** and is not the real-use baseline to preserve. Real Lina use will begin from a **fresh database** on the current schema.

The Product Owner approved a launch-first Daily-Use Release 1. The governing launch addendum is `docs/DAILY_USE_RELEASE_PLAN.md`; approved launch decisions are summarized in `docs/DAILY_USE_RELEASE_DECISIONS.md`; the bounded current task overlay is `project-state/DAILY_USE_RELEASE_TASKS.md`. `TASKS.md` remains the preserved historical task ledger.

The approved execution sequence is intentionally sequential:

```text
RL-01A Accepted Runtime Alignment
→ RL-01B Fresh DB + Runtime Composition
→ RL-01C Clerk + OpenAI Operational Verification
→ RL-01D Controlled Full Intelligence Loop
→ TASK-027A Student Core Profile
→ PF-01 Personal Facts Contract
→ PF-02 Personal Facts Extraction/Reconciliation
→ PF-03 Relevant Facts in Tutor Context
→ FE-01 Lina Visual System & Reuse Decision
→ FE-02 Daily Student Experience
→ TASK-032 Voice / STT
→ TASK-033 Vision / Student Work
→ TASK-034 Original-Image Annotation
→ DEPLOY-01 Private Daily Environment
→ LINA-R1 Clean Real-Use Baseline
```

Only **RL-01A** is currently executable. Do not start later tasks early.

---

## Current reality

- The accepted remote branch was `codex/ctx-03` at `af7264cd05e1bb9f6e794005802758521c57d509` when the Daily-Use Release plan was approved; subsequent commits on the branch are governing-document updates for this approved transition unless later runtime work is explicitly accepted.
- The prior local audit observed an isolated worktree at an older local revision and an older live runtime/database. Therefore the first execution task is revision/runtime alignment, not feature work.
- Full-System Learning Intelligence Acceptance remains **DONE / ACCEPTED**. Canonical authority remains **Segment-Scoped Semantic Review + Session-Scoped deterministic Intelligence Finalization**.
- One primary Tutor model call per normal Student turn remains protected.
- Existing DB-backed jobs/Worker, PostgreSQL/pgvector, Clerk integration, Model Gateway/OpenAI route, hybrid retrieval, object-storage abstraction, and Student Tutor path are implemented foundations.
- The current standard project workflow starts Web + API but does not start the Worker. This is an operational composition gap, not a missing Learning Intelligence subsystem.
- The historical/test database will not be migrated as Lina's real-use baseline. The real-use baseline will start from a fresh migrated database with no experimental interaction history.
- Limited historical Real-Lina interaction remains a verified historical fact, but it will not be treated as the longitudinal production baseline.
- Current hybrid RAG is already project-owned Docling + PostgreSQL/pgvector lexical/vector retrieval with provenance. It remains the baseline; replacement requires a later measured evaluation, not assumption.

---

## Active decisions

1. **Launch-first execution:** finish the smallest reliable private daily-use product so Lina can start using it, then expand from real use.
2. **Fresh real-use data:** the current historical database is experimental. Real Lina use begins from a clean database on the current schema.
3. **Personal Facts:** add a separate Personal Facts layer containing durable facts asserted by the Student about herself. It is separate from Student Core Profile, Conversation Context, and Learning Intelligence.
4. **Personal Facts boundaries:** no personality/psychological diagnosis, no learning conclusions, no transcript-summary memory, and no conversion of Personal Facts into Learning Evidence.
5. **Fact evolution:** facts are source-linked, temporal, revisable, and may be supported, contradicted, or superseded over time.
6. **Parent visibility:** Parent may see the stored Personal Facts. Parent-supplied claims do not become the Student's Personal Facts merely because the Parent asserted them.
7. **Future parent insights:** combining Personal Facts with Learning Intelligence for exploratory Parent insights is intentionally deferred until real data exists. No talent-detection/ML architecture is authorized now.
8. **Renderer-first visual teaching:** accurate reusable React/SVG/renderer paths are the primary learning-visual strategy. OpenAI image generation is optional/deferred and not the default teaching renderer.
9. **Student image feedback:** preserve the original Student image as raw source; annotation on the original is the default derived visual response; clean reconstruction is fallback when annotation is insufficient.
10. **Frontend is launch scope:** Lina's Student UX must become visually engaging, child-appropriate, polished, and coherent before daily use. Reuse candidates must be evaluated selectively rather than stacking many UI libraries.
11. **Voice:** initial Voice is Audio → STT → transcript → normal Tutor path. No speech-to-speech requirement for Release 1; successful STT does not retain raw audio under current policy.
12. **Vision:** Student work/photo understanding is promoted into the launch sequence after the core environment and frontend foundations are verified.
13. **RAG:** keep current hybrid retrieval for launch. Post-launch RAG evaluation may compare current native retrieval with LlamaIndex/Docling and OpenAI retrieval options using a real golden set.
14. **Provider boundary:** AI capabilities remain behind Model Gateway; application domains do not hardwire OpenAI SDK calls directly.
15. **Deployment:** Replit remains a candidate private daily-use host, not architecture. Final deployment follows proof of the current composition.

---

## Protected areas

```text
Raw learning interaction
→ completed Segment semantic interpretation
→ Session-authorized Event/Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ relevant later learning personalization
```

Also protected:

- current behavior outranking history;
- one primary Tutor model call per normal turn;
- deterministic Session Finalization and no partial Session activation;
- Candidate metadata remaining provisional;
- Personal Facts remaining separate from Learner Intelligence and never becoming Learning Evidence by identity;
- Student Core Profile remaining authoritative Parent/System factual state, distinct from Student-asserted Personal Facts;
- Safety, conversation context, RAG, Personal Facts, Student Core Profile, and Learner Intelligence remaining separate inputs/authorities;
- original Student images/work remaining raw source; annotations/reconstructions remain derived;
- no graph database, second learner-memory system, Redis/Celery, microservice split, or deployment redesign without demonstrated need;
- current hybrid Retrieval domain remaining replaceable and provenance-preserving;
- no future Parent Insight conclusion writing back into Personal Facts or Learning Intelligence.

---

## Active risks

- **RL-R1 — Accepted Runtime Not Yet Unified — Criticality 5**  
  Local/current operational execution must first align to the accepted revision and stop using stale runtime components as authority.

- **RL-R2 — Daily Runtime Composition Unverified — Criticality 5**  
  Fresh PostgreSQL + current Web + API + Worker + Clerk + real Model Gateway route have not yet been proven together as one recurring environment.

- **UX-R1 — Daily-Use Experience Not Yet Ready — Criticality 4**  
  Current Student UI is a proving surface, not yet the approved Daily-Use Lina frontend with Voice/photo affordances and richer visual identity.

- **PF-R1 — Personal Facts Not Yet Captured — Criticality 4**  
  The real-use database should ideally begin with Personal Facts support so this durable user-context stream starts from Lina's first clean sessions.

- **VISION-R1 — Durable Student Asset Hosting Required Before Daily Vision — Criticality 4**  
  Local storage is adequate for controlled verification but daily photographed work requires durable/private storage and restart-safe access.

- **MATH-01 — Structured Math Readability — Criticality 4**  
  Remains independent. Renderer-first direction does not silently authorize the full Artifact Engine before its scheduled task.

- **ID-01 — Concurrent First-Identity Creation Race — Criticality 3**  
  Remains investigation-only until reproduced; it must not block unrelated launch work unless the real auth verification reproduces it.

---

## Current executable task

### RL-01A — Accepted Runtime Alignment

**Status:** READY  
**Authority:** `project-state/DAILY_USE_RELEASE_TASKS.md`  
**Boundary:** Repository/runtime alignment only. Do not create the fresh real-use DB, start Worker against real data, implement Personal Facts, redesign frontend, add Voice/Vision, deploy, or change RAG in this task.

**Goal:** Align the isolated implementation worktree and runtime reference to the current accepted `codex/ctx-03` revision and produce a verified starting point for RL-01B.

---

## Next recommended action

Execute **RL-01A only**, verify it, update current task/project state, and return for review before RL-01B is promoted.

Do not execute RL-01B or any feature track in the same run.

---

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/DAILY_USE_RELEASE_PLAN.md`
- `docs/DAILY_USE_RELEASE_DECISIONS.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/CHILD_SAFETY_POLICY.md`
- `docs/TECHNOLOGY_REUSE_CATALOG.md`
- `project-state/DAILY_USE_RELEASE_TASKS.md`
- `TASKS.md`
- `project-state/SYSTEM_MAP.html`
