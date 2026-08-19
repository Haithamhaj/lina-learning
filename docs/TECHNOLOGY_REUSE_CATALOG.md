# TECHNOLOGY_REUSE_CATALOG.md — Lina Personal Learning System

**Status:** Approved implementation reference  
**Purpose:** Reuse proven libraries, components, templates, and framework integrations before building substantial UI, chat, retrieval, or learning-artifact infrastructure from scratch.  
**Authority:** This catalog does not override `PROJECT_REFERENCE.md`, `LEARNING_INTELLIGENCE_SPEC.md`, `CHILD_SAFETY_POLICY.md`, or `IMPLEMENTATION_PLAN.md`. It constrains implementation choices by requiring an explicit reuse check where applicable.

---

# 1. Governing Principle

> **Reuse-first, not dependency-first.**

Before building a substantial subsystem from scratch, inspect the approved candidates in this catalog. Reuse or adapt an existing option when it:

1. preserves the project's approved architectural boundaries,
2. materially reduces implementation or maintenance complexity,
3. remains replaceable behind a local adapter/component boundary,
4. does not force unrelated product concepts into Lina's system,
5. keeps the Student experience simple and child-appropriate,
6. has acceptable current licensing/usage terms,
7. can be verified with the same project tests and observability expectations as custom code.

Do **not** adopt an entire platform merely because one useful component exists inside it.

A custom implementation is preferred when a reusable option creates more coupling, hides critical behavior, conflicts with FastAPI/Next.js boundaries, weakens traceability, or makes the product harder to modify.

---

# 2. Status Meanings

| Status | Meaning |
|---|---|
| **ADOPT BASELINE** | Approved default unless implementation evidence shows a concrete conflict. |
| **EVALUATE BEFORE CUSTOM BUILD** | Codex must perform a focused fit check before writing equivalent infrastructure from scratch. |
| **RECOMMENDED SOURCE** | Good source of reusable components/patterns; use selectively rather than as a required dependency. |
| **VISUAL REFERENCE ONLY** | Use for visual direction/benchmarking; do not copy the product architecture or full template codebase by default. |
| **OPTIONAL / ON DEMAND** | Add only when a real learning or product use case requires it. |
| **AVOID AS FOUNDATION** | May contain useful ideas, but should not become a core dependency or architectural base without explicit approval. |

For every `EVALUATE BEFORE CUSTOM BUILD` item, the implementing task should record a concise decision: **ADOPT / PARTIAL ADOPT / REJECT**, plus the reason.

---

# 3. Core Web UI Foundation

## 3.1 shadcn/ui

**Status:** ADOPT BASELINE  
**Area:** Base application UI and Parent/Admin shell  
**Use for:** Buttons, cards, dialogs, inputs, drawers, sidebars, tables, forms, accessibility-friendly primitives, dashboard/application blocks.

### Why it fits

- Works naturally with React/Next.js and Tailwind-based product styling.
- Components/blocks are intended to be brought into the application and customized rather than forcing a closed visual system.
- Reduces basic UI plumbing while preserving ownership of Lina's visual identity.

### Rules

- Treat shadcn/ui as the **functional base**, not the final Lina aesthetic.
- Student-facing components should be restyled for Lina's age, personality, colors, motion, and interaction needs.
- Parent/Admin can stay more restrained and utilitarian.

**Official reference:** https://ui.shadcn.com/blocks

---

# 4. Student Chat / Tutor Interface

## 4.1 assistant-ui

**Status:** EVALUATE BEFORE CUSTOM BUILD — preferred first candidate  
**Area:** Student Tutor conversation UI  
**Use for:** Thread/message primitives, composer, attachments, persistence adapters, custom backend runtime integration, future speech/feedback hooks.

### Why it fits

- Supports React chat UI against a custom AI backend rather than requiring model execution inside the frontend.
- Has explicit runtime/adapters for attachments and persistence.
- Could reduce custom work for message/thread/composer behavior while FastAPI remains the authority for Tutor runtime, safety, context, and AI execution.

### Fit check required before custom chat UI

Validate that it can support:

- FastAPI/SSE or an adapter around the approved streaming contract,
- server-owned session/thread persistence,
- Lina image/drawing/file attachments through project-owned object storage,
- custom message parts for Learning Artifact cards and future annotations,
- the upstream `SafetyDecision` flow,
- no provider-specific model coupling,
- easy child-specific visual customization,
- no hidden conflict with Candidate Event metadata or observability.

### Adoption rule

Use it if it reduces chat plumbing **without owning Tutor logic**. Reject or partially adopt if fitting it to the approved runtime requires more complexity than a local custom shell.

**Official references:**  
https://www.assistant-ui.com/docs/runtimes/custom/overview  
https://www.assistant-ui.com/docs/guides/attachments

---

# 5. Lina Visual Design & Child-Friendly Motion Sources

These sources are **not** permission to make the interface visually noisy. The target is:

> **playful + intelligent + colorful + personal**, suitable for approximately age 10 — not preschool, not corporate dashboard, and not motion for motion's sake.

The Student UI should be able to feature Lina's photo/avatar prominently if the Parent chooses, with large clear cards, warm illustration/shape language, simple navigation, and meaningful motion.

## 5.1 Motion Primitives

**Status:** RECOMMENDED SOURCE  
**Use for:** Polished dialogs, animated groups/backgrounds, carousels, in-view transitions, text effects, subtle motion primitives built on Motion/Tailwind.

### Rule

Prefer for interaction polish when the motion supports orientation, feedback, focus, celebration, or learning flow.

**Official reference:** https://motion-primitives.com/docs

## 5.2 Magic UI

**Status:** RECOMMENDED SOURCE — selective use  
**Use for:** Confetti, sparkles, ripple buttons, animated grids, playful text/background accents, celebration moments.

### Rule

Use as accents only. Do not turn the Tutor into an amusement interface or distract from the learning objective.

**Official reference:** https://magicui.design/docs/components

## 5.3 React Bits

**Status:** RECOMMENDED SOURCE  
**Use for:** Animated React interactions/effects and inspiration for playful transitions.

### Rule

Prefer components with clear UX value. Avoid cursor-heavy, distortion-heavy, or decorative effects that reduce readability or performance.

**Official reference:** https://reactbits.dev/get-started/index

## 5.4 21st.dev

**Status:** RECOMMENDED SOURCE  
**Use for:** React/Tailwind cards, profiles, AI chat components, file uploads, dashboards, onboarding, and full-screen patterns that Codex can inspect/adapt quickly.

### Why it is useful for Codex

The component library is explicitly structured for copy/prompt workflows with AI coding assistants, making it useful as a discovery/catalog layer before custom component work.

### Rule

Use it to discover/adapt specific components or screen patterns. Do not assemble Lina's product from unrelated community components without a coherent design system.

**Official reference:** https://help.21st.dev/

## 5.5 Aceternity UI

**Status:** RECOMMENDED SOURCE — selective  
**Use for:** Higher-polish microinteractions, image effects, animated modals, hero/background treatments, selected interactive cards.

### Rule

Many components are visually strong; use only those that fit Lina's visual language and do not dominate the learning content.

**Official reference:** https://ui.aceternity.com/components

## 5.6 Cult UI

**Status:** OPTIONAL / ON DEMAND  
**Use for:** Additional animated components that fit the shadcn workflow.

### Rule

Do not add it solely because a similar component already exists in the approved base or other sources.

**Official reference:** https://www.cult-ui.com/docs

---

# 6. Child / Education Visual Template References

## 6.1 Framer Education Marketplace

**Status:** VISUAL REFERENCE ONLY  
**Use for:** Layout inspiration, educational cards, onboarding, illustration placement, typography, responsive composition.

**Official reference:** https://www.framer.com/marketplace/templates/category/education/

## 6.2 Webflow Kids Education Templates

**Status:** VISUAL REFERENCE ONLY  
**Use for:** Color, illustration, playful composition, child-focused visual language.

### Important constraint

Many available templates target preschool/daycare audiences. Lina's interface should feel appropriate for a roughly 10-year-old child, so Codex must **borrow visual principles, not preschool styling**.

**Official reference:** https://webflow.com/templates/search/kids-education

## Visual-template rule

Do not adopt a complete Webflow/Framer marketing template as the application architecture. Extract useful design references into the Next.js design system and application shell.

---

# 7. Learning Artifact Renderer Stack

The approved architecture remains:

```text
Tutor teaching decision
        ↓
Typed Artifact Specification
        ↓
Artifact Registry
        ↓
Approved renderer
        ↓
Inline Artifact or Learning Canvas
```

The AI should describe **what educational representation is needed**. Reusable renderers should determine **how it is rendered** whenever possible.

## 7.1 Native React + SVG

**Status:** ADOPT BASELINE  
**Use for:** Most simple visual learning artifacts and diagrams.

## 7.2 Motion

**Status:** ADOPT BASELINE  
**Use for:** Meaningful animation, gestures, drag, transitions, SVG animation.

## 7.3 JSXGraph

**Status:** ADOPT BASELINE — Math  
**Use for:** Number lines, geometry, coordinates, sliders, function/graph exploration, interactive mathematical constructions.

## 7.4 React Konva

**Status:** ADOPT BASELINE — spatial interaction  
**Use for:** Canvas-based drag/drop, arranging objects, labeling, spatial tasks, interactive diagrams.

## 7.5 MathLive

**Status:** ADOPT BASELINE — Math input  
**Use for:** Editable mathematical input, fractions, symbols, age-appropriate math keyboard experiences.

## 7.6 Rough.js

**Status:** OPTIONAL / ON DEMAND  
**Use for:** Hand-drawn/sketch visual treatment when it improves warmth or explanatory style.

## 7.7 Recharts

**Status:** OPTIONAL / ON DEMAND  
**Use for:** Actual data charts in Science/Math rather than hand-building chart primitives.

## 7.8 p5.js

**Status:** OPTIONAL / ON DEMAND  
**Use for:** Simulations such as particles, motion, forces, or science behavior where React/SVG/Konva are insufficient.

## 7.9 React Flow

**Status:** OPTIONAL / ON DEMAND  
**Use for:** Node/edge interactive models such as ecosystems or process relationships if a real use case requires it.

## 7.10 Mermaid

**Status:** OPTIONAL / INTERNAL REFERENCE  
**Use for:** Quick documentation/Parent/Admin diagrams; not the default child-learning renderer.

## 7.11 Sandpack

**Status:** DEV TOOL ONLY / ON DEMAND  
**Use for:** Isolated development/testing of generated/custom interactive code where helpful; not the normal Student artifact runtime.

---

# 8. OpenMAIC Artifact Infrastructure

## 8.1 `@openmaic/*` DSL / renderer / importer SDK family

**Status:** EVALUATE BEFORE CUSTOM BUILD  
**Area:** Interactive Learning Artifact DSL/renderer infrastructure

### Why it matters

OpenMAIC has separated its DSL/renderer/importer functionality into standalone packages. This is close to the project's approved idea of:

```text
Typed Artifact Spec → Renderer → Interactive learning scene
```

### Mandatory fit check before building a generic custom Artifact Engine

Evaluate whether the relevant OpenMAIC SDK packages can be used or adapted while preserving:

- Lina's typed Artifact Spec contract,
- project-owned Tutor and Learning Intelligence architecture,
- Next.js integration,
- safe/sandboxed custom-interactive behavior,
- meaningful artifact interaction events,
- renderer replaceability,
- child-specific design control,
- no dependency on OpenMAIC's multi-agent classroom product model.

### Adoption rule

Prefer **partial/package-level reuse** if useful. Do not adopt the OpenMAIC application/platform architecture merely to obtain its renderer.

### License note

OpenMAIC states that the project was relicensed to MIT in v0.3.0. Codex must still verify the current package/repository license before adoption.

**Official reference:** https://github.com/THU-MAIC/OpenMAIC

---

# 9. Document Understanding & RAG Reuse

## 9.1 Docling

**Status:** ADOPT BASELINE  
**Role:** Structural document understanding and versioned `DoclingDocument` representation.

The existing project decision remains unchanged: Docling provides document structure; the Lina system owns educational semantics.

## 9.2 Native Docling + PostgreSQL/pgvector

**Status:** BASELINE RETRIEVAL PATH  
**Use for:** Hierarchical/Hybrid Docling content units, project-owned metadata, lexical retrieval, pgvector retrieval, project-owned ranking/context selection.

### Strength

Lowest framework coupling and maximum control over Grade/Subject/Focus/Concept filtering and source provenance.

## 9.3 LlamaIndex + official Docling integration

**Status:** EVALUATE BEFORE CUSTOM RAG PLUMBING  
**Use for:** `Docling Reader` / `Docling Node Parser` and retrieval/index plumbing if it meaningfully reduces custom code while preserving project metadata and retrieval policy.

### Required spike

Before implementing large amounts of custom retrieval/index plumbing, compare:

**Option A**
```text
DoclingDocument
→ project structural blocks
→ lexical + pgvector
→ project retrieval service
```

**Option B**
```text
DoclingDocument
→ official LlamaIndex Docling Reader / Node Parser
→ project-compatible index/retrieval layer
```

Evaluate:

- provenance preservation,
- Grade/Subject/Current Focus filtering,
- figure/formula metadata,
- context-budget control,
- golden-set retrieval quality,
- amount of custom plumbing removed,
- dependency complexity,
- rebuildability,
- ability to keep the Retrieval domain replaceable.

### Adoption rule

Use LlamaIndex only if the spike demonstrates lower total complexity without weakening the approved retrieval behavior. Do not adopt a framework simply because integration exists.

**Official reference:** https://docling-project.github.io/docling/integrations/llamaindex/

---

# 10. Approved Reuse Decision Matrix

| Area | Candidate | Status | Codex instruction |
|---|---|---|---|
| Base UI | shadcn/ui | **ADOPT BASELINE** | Use as the functional React UI base and customize. |
| Student chat | assistant-ui | **EVALUATE BEFORE CUSTOM BUILD** | Spike custom-runtime fit before hand-building full thread/composer plumbing. |
| Child motion | Motion Primitives | **RECOMMENDED SOURCE** | Reuse selectively for meaningful interaction polish. |
| Playful accents | Magic UI | **RECOMMENDED SOURCE** | Use sparingly for child-friendly delight/feedback. |
| Animated components | React Bits | **RECOMMENDED SOURCE** | Inspect before custom effects; avoid distracting components. |
| AI-friendly component discovery | 21st.dev | **RECOMMENDED SOURCE** | Inspect/adapt specific components/screens. |
| Premium microinteractions | Aceternity UI | **RECOMMENDED SOURCE** | Selective; do not let visual effects dominate. |
| Additional shadcn motion | Cult UI | **OPTIONAL** | Use only when it clearly fills a gap. |
| Student visual direction | Framer Education templates | **VISUAL REFERENCE ONLY** | Borrow composition/design language, not architecture. |
| Child visual direction | Webflow Kids Education templates | **VISUAL REFERENCE ONLY** | Borrow color/illustration ideas; avoid preschool feel. |
| Math/visual artifacts | React/SVG + Motion + JSXGraph + Konva + MathLive | **ADOPT BASELINE** | Approved renderer stack. |
| Artifact DSL/renderer | OpenMAIC SDK packages | **EVALUATE BEFORE CUSTOM BUILD** | Evaluate package-level reuse before generic custom renderer infrastructure. |
| Document understanding | Docling | **ADOPT BASELINE** | Keep behind project adapter. |
| RAG plumbing | Native Docling + pgvector | **BASELINE** | Default simplest path. |
| RAG framework acceleration | LlamaIndex + Docling | **EVALUATE BEFORE CUSTOM BUILD** | Run focused spike; adopt only if total complexity falls. |

---

# 11. Reuse Evaluation Checklist for Codex

Before custom-building a subsystem covered by this catalog, answer:

1. Which approved candidate(s) were inspected?
2. What exact project problem would reuse solve?
3. What code/infrastructure would it eliminate?
4. Does it preserve FastAPI/Next.js/domain boundaries?
5. Can it stay behind a local adapter/component interface?
6. Does it preserve safety, observability, provenance, and rebuildability?
7. Does it introduce provider/platform lock-in?
8. Is the dependency/license acceptable for the intended use?
9. Is the Student UX easier to customize for Lina than a custom implementation?
10. Final decision: **ADOPT / PARTIAL ADOPT / REJECT**, and why?

A task requiring an `EVALUATE BEFORE CUSTOM BUILD` candidate is not complete until this decision is recorded in the task completion notes/change summary.

---

# 12. Explicit Anti-Patterns

Do not:

- clone a full education/kids template and force the product architecture into it,
- adopt an entire AI-learning platform to obtain one renderer,
- install multiple overlapping animation/component libraries without a specific use,
- let community UI sources fragment Lina's design language,
- adopt LlamaIndex or another RAG framework before comparing it with the simpler native Docling/pgvector path,
- let assistant-ui or any frontend library own Tutor reasoning, safety, session truth, or Learning Intelligence,
- generate arbitrary HTML/JavaScript for routine learning visuals when a typed renderer already fits,
- select the most visually impressive component when a simpler one is clearer for a 10-year-old learner.

---

# 13. Maintenance Rule

This catalog is expected to evolve as tools change.

When a candidate is actually evaluated:

- record the implementation decision,
- update its status if appropriate,
- preserve the architectural reason,
- remove stale candidates rather than accumulating an ever-growing technology list.

The product architecture remains authoritative over this catalog.
