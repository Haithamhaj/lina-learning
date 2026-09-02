# CURR-RENDER-MATH-01 — Grade 5 Math Renderer Planning Brief

**Status:** Research / planning only. Non-authoritative until Product Owner review and task promotion.
**Research date:** 2026-09-02
**Scope:** Grade 5 Mathematics capability planning for Lina Learning Studio.
**Not an implementation authorization.**

## Purpose

Lina is a Grade 5 learner in an international American-curriculum school in Riyadh. Her known program is McGraw-Hill *My Math*, but the edition, ISBN, volumes, chapter order, and school pacing are not available. This study identifies reusable mathematical capabilities—not textbook pages or exercises—so an eventual Studio can choose a safe, typed representation from a small catalog.

The durable unit of planning is:

```text
Concept + representation + interaction + validator + accessible fallback
```

The catalog is not a My Math replacement, a lesson sequence, a generic Canvas, or a claim that Canvas should appear on every turn. The missing edition does not block concept preparation because the selected concept map is grounded in Grade 5 standards; a later alignment layer maps the school's actual material to these stable capability keys.

## Repository and architecture fit

The repository already separates Content/ Retrieval from Tutor and reserves a typed Artifact Specification → Registry → approved renderer path. Studio research further requires application-owned semantic event history, materialized snapshots, deterministic renderers for routine work, and one Student-facing Tutor. This pack therefore proposes only subject-owned catalog data: it must not put fraction, coordinate, or arithmetic fields into a generic Studio Core.

The present code has a source-linked `ContentDocument` / Docling / hybrid `RetrievalService` path and a provider-neutral Model Gateway, but no Learning Artifact or Studio runtime to alter. The Studio prototype, FE-02, database, retrieval, Tutor, and intelligence remain untouched.

## Research method

1. Audited the governing documents, Studio synthesis, current project state, Content/Retrieval/Tutor/Model Gateway interfaces, and current source-provenance direction.
2. Used the official Common Core Grade 5 standards as the capability baseline; AERO Common Core mapping was reviewed as international-school context, not assumed school authority.
3. Used official IM Grade 5 material as an aligned curriculum and representation/routine reference; used the federal WWC representation guidance to avoid treating visual novelty as learning value.
4. Reviewed public McGraw-Hill material only to confirm the program context, not to infer this school's edition or sequence.
5. Recorded every external source and its rights posture in [07_SOURCE_LICENSE_MANIFEST.md](07_SOURCE_LICENSE_MANIFEST.md). No lesson, exercise, image, page, or code was copied or ingested.

## Build-time vs runtime boundary

```text
Build time: standards and trusted references → concept/representation analysis → capability catalog
Runtime: current question or captured work → optional RetrievalService grounding → choose/configure allowlisted capability
```

The future Trusted Educational Reference Pack may share source identity, alignment class, concept keys, and provenance with this work. It remains a separate runtime/background grounding capability. It must use the existing Learning Source and Retrieval boundary rather than introduce a second RAG system. The current question remains authoritative, and absence of a source or renderer never blocks Tutor availability.

## Explicit non-decisions

- No renderer, Studio event, schema, validator, dependency, runtime, or FE-02 code is created.
- No model call, Canvas specialist, generation policy, or package adoption is approved.
- No exact My Math edition or lesson order is asserted.
- No source is approved for automated ingestion merely because it informed research.
- No renderer interaction is automatically Learning Intelligence evidence; only later policy-approved, meaningful semantic actions could be considered.

## Acceptance criteria for this study

- A standards-grounded Grade 5 concept map with stable proposed keys.
- A traceable concept → representation → renderer → validator mapping.
- A deliberately small, ranked renderer foundation with a transparent coverage denominator.
- Accessible, keyboard/touch, RTL/LTR, mobile, failure, and photo-work considerations for each renderer family.
- Source/rights decisions that keep proprietary and restricted material out of product dependency.
- A McGraw alignment placeholder that can be completed without changing the renderer catalog.

## Confidence

**High** for Grade 5 capability coverage and the deterministic-first boundary. **Medium** for the exact best first renderer batch until a Product Owner selects the proof objective and real Lina use validates it. **Low / intentionally unknown** for McGraw edition-specific alignment.
