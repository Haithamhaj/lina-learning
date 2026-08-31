# Lina Personal Learning System — Project State

## Current goal

`SUBJ-01 — Subject Attribution at Segment/Finding/Event Boundaries` is **DONE / CODE REVIEW VERIFIED / ACCEPTED**. `DEC-01 — Mode / Strategy / Prior-Relation Calibration` is **DONE / CODE REVIEW VERIFIED / ACCEPTED**. `DEC-02 — TeachingMethod Attribution Fidelity` is **DONE / DEFECT NOT REPRODUCED / ACCEPTED**. `REP-01 — Over-Practice / Repetition Control` is **DONE / CODE REVIEW VERIFIED / ACCEPTED**. `LANG-01 — Language Continuity` is **DONE / CODE REVIEW VERIFIED / ACCEPTED**. `CAND-03 — Candidate Output / Runtime Constraint Alignment` is **DONE / CODE REVIEW VERIFIED / ACCEPTED**. `CAND-02 — Guided vs Independent Candidate Consistency` is **DONE / CODE REVIEW VERIFIED / ACCEPTED**. The Tutor Semantic Calibration sequence is complete: DEC-01 → DEC-02 → REP-01 → LANG-01 → CAND-02. The next action is Product Owner selection of the next independent open track; do not begin a new task in this transition.

`SCOPE-01 — Cross-Subject Conversation & Subject Policy` is **DONE / APPROVED** and is governed by `docs/SUBJECT_SCOPE_POLICY.md`.

Full-System Learning Intelligence Acceptance remains **DONE / ACCEPTED**. The accepted semantic architecture remains:

> **Segment-Scoped Semantic Review + Session-Scoped Intelligence Authority**

---

## Current reality

- `SEG-EVID-01A–F` are DONE / ACCEPTED; the full Math Learning Intelligence path is accepted by independent code review.
- Segment Review is the semantic-analysis unit; Session Finalization is deterministic and remains the durable Evidence authority.
- One primary Tutor model call per normal Student turn remains protected. No second normal-turn classifier/summarizer/evidence call is approved.
- Candidate Events remain provisional hints only; raw interaction outranks Candidate metadata.
- Current behavior outranks historical personalization.
- Reprocessing remains externally Session/date-scoped with atomic authority activation and auditable prior generations.
- Real-Lina validation remains deferred; browser verification remains separate and must not be claimed unless executed.
- The current implementation is still Math-first, but Math is no longer the governing product assumption for Session-level Subject authority.
- SUBJ-01 is DONE / CODE REVIEW VERIFIED / ACCEPTED. It preserves Segment Review v3, deterministic conflict-fail-closed materialization, reviewed-Subject attribution, v8 primary-Tutor-call provisional Broad Subject prefiltering, retention provenance, and reprocessing behavior. Independent GitHub review verified the correction; automated test execution remains CODEX-REPORTED and bounded real `openai/gpt-5.6-luna` execution remains CODEX-REPORTED REAL LUNA VERIFIED. No migration was required.
- Browser and Real-Lina remain NOT VERIFIED and must not be implied by automated or synthetic real-model checks; neither blocks SUBJ-01 closure.
- DEC-01 is DONE / CODE REVIEW VERIFIED / ACCEPTED. It retains one primary Tutor call and `tutor_turn_v8`. Its compact, canonical PriorMethodRelation guidance contrastively requires `CONTINUATION` for short direct continuations/direct answers absent a Student evaluation, `DID_NOT_HELP` only for explicit dissatisfaction, and `HELPED` only for explicit helped signals. Independent GitHub review verified the bounded correction. Automated verification remains CODEX-REPORTED and bounded real `openai/gpt-5.6-luna` verification remains CODEX-REPORTED REAL LUNA VERIFIED; Browser and Real-Lina remain NOT VERIFIED.
- DEC-02 is DONE / DEFECT NOT REPRODUCED / ACCEPTED. Independent architecture/code review accepted the bounded diagnostic: visible Tutor text and TeachingMethod identity come from the same primary `tutor_turn_v8` Luna call; raw method identity equals the persisted Tutor-message value with `teaching-method-registry-v1` provenance; and Segment Review requires persisted method ID → exact Tutor message → later Student outcome. The sample exercised CONCRETE_EXAMPLE, VISUAL_REPRESENTATION, WORKED_EXAMPLE, ANALOGY, and DECOMPOSITION; SOCRATIC_FOCUS and SYMBOLIC_EXPLANATION were not exercised. Automated verification remains CODEX-REPORTED and real `openai/gpt-5.6-luna` diagnostic remains CODEX-REPORTED REAL LUNA VERIFIED; Browser and Real-Lina remain NOT VERIFIED.
- REP-01 is DONE / CODE REVIEW VERIFIED / ACCEPTED. Independent GitHub review verified the compact same-primary-Luna-call guidance correction: it favors meaningful variation, deeper reasoning, transfer, useful progression, restoring Student agency, or a natural close after repeated independently reasoned current-Segment success; it avoids low-information near-identical drills without inferring mastery or introducing a threshold. Useful reinforcement remains allowed for fragile, supported, uncertain, contradictory, recently repaired, or genuinely different work. Automated verification remains CODEX-REPORTED; bounded real `openai/gpt-5.6-luna` verification remains CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED and are not closure blockers.
- LANG-01 is DONE / CODE REVIEW VERIFIED / ACCEPTED. Independent GitHub review verified the bounded same-primary-Tutor language-guidance correction: a language-neutral number, fraction, equation, mathematical expression, or answer-choice symbol is not a language switch and cannot select Arabic or English; the immediate active exchange/current context preserves the established conversational language, while a clear current Arabic/English message still overrides it and natural bilingual school/math terminology remains allowed. CTX-03, `tutor_turn_v8`, context selection, and model-call count are unchanged. Automated verification remains CODEX-REPORTED; bounded real `openai/gpt-5.6-luna` verification remains CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED and are not closure blockers.
- CAND-02 is DONE / CODE REVIEW VERIFIED / ACCEPTED. Independent GitHub review verified the compact same-primary-Tutor Candidate guidance calibration: `independent_success` requires an observed target response without meaningful task-specific support, while `guided_success` requires immediate task-specific scaffolding that materially enables or narrows that response. Candidate metadata remains provisional; Segment Review remains the later semantic authority and Session Finalization remains the durable intelligence authority. Automated verification remains CODEX-REPORTED; bounded real `openai/gpt-5.6-luna` verification remains CODEX-REPORTED REAL LUNA VERIFIED. Browser and Real-Lina remain NOT VERIFIED and are not closure blockers.

### SCOPE-01 approved policy

- one technical Session may contain multiple session-local Segments / Learning Threads with different Subjects;
- Lina does not need separate chats per Subject;
- one Learning Segment has one primary Broad Subject;
- current Student intent outranks stale prior Subject/source context;
- `LEARNING` and `NON_LEARNING / CASUAL` Segments are distinct;
- Non-Learning/Casual Segments create no academic learning Evidence;
- Broad Subjects use a controlled, versioned, extensible registry;
- Core classification is `broad_subject + concept/topic`;
- school Subject/Domain Path/Unit/Lesson/Page context is optional and source-grounded;
- no school source means `school_relation = UNKNOWN`, not automatically `EXTENDED`;
- actual Lina school Subjects come from trusted Parent/Admin or school sources when available;
- future photographed pages/work may strengthen grounding but page identity alone is not learner Evidence;
- future Adaptive/Open and School-Focused/Book-Led Parent policies must share the same Learning Intelligence Core.

### SUBJ-01 implementation contract

`docs/SUBJ_01_IMPLEMENTATION_SPEC.md` is the approved execution contract.

The new Segment Review path must make reviewed Segment Subject the durable attribution source for new Event/Evidence materialization. `LearningSession.subject` may remain for legacy/current-entry compatibility but must not stamp cross-subject Evidence blindly.

The next Review contract must replace relative Session-subject semantics with actual reviewed Broad Subject attribution and replace binary school/extended semantics with the approved three-state school relationship while preserving historical contract auditability.

---

## Active decisions

1. **Segment interprets. Session commits.**
2. **Current Student intent outranks stale context.**
3. **One Learning Segment = one primary Broad Subject.**
4. **Broad Subject is controlled; school structure is optional and sourced.**
5. **No extra normal-turn Subject classifier.**
6. **New Event/Evidence Subject comes from reviewed Segment/Finding authority, not a fixed Session default.**
7. **Subject uncertainty/conflict fails closed for durable Evidence.**
8. **Future School-Focused mode reuses the same Evidence/State/Pattern architecture.**
9. **PriorMethodRelation remains a one-primary-call Luna semantic decision; compact contrastive guidance calibrates it without deterministic natural-language routing.**

---

## Protected areas

```text
Raw interaction provenance
→ completed Segment semantic interpretation
→ Session-authorized Evidence
→ Current State / Patterns
→ Learner Intelligence Card
→ personalization
```

Also protected:

- one primary Tutor call per normal turn;
- deterministic Session Finalization;
- no partial Session activation;
- exact Segment Review/Finding/Event/Evidence provenance;
- current behavior outranking history;
- safety, conversation context, school/RAG context, Student Core Profile, and Learner Intelligence remaining separate authorities;
- no second learner-memory/counter system.

---

## Active risks

- **SUBJ-R1 — Wrong Subject Evidence Contamination — Criticality 5**  
  New Event/Evidence must not inherit a stale Session-level Subject.

- **SUBJ-R2 — Segment Boundary / Subject Conflict — Criticality 5**  
  A Finding that clearly belongs to another Subject must fail closed and remain auditable rather than being silently relabeled.

- **SUBJ-R3 — Legacy/New Contract Compatibility — Criticality 5**  
  Existing `subject_alignment`, `school_or_extended`, Math-first Session data, retention provenance, and reprocessing generations must remain auditable.

- **SUBJ-R4 — Accidental Extra AI Call — Criticality 5**  
  Subject support must not introduce a normal-turn classifier/summarizer call.

- **SUBJ-R5 — School Context Becoming Teaching Authority — Criticality 4**  
  Optional outline/book/plan data must improve alignment without blocking open learning.

- **STATE-01 — Structured Segment State lineage reliability — OPEN / NON-BLOCKING — Criticality 3**

---

## Next recommended action

Product Owner selection of the next independent open track is the next action. No existing governing record promotes MATH-01, ID-01, EDU-ERR-01, REC-25, or LR-D04B automatically. Do not begin a new task in this transition.

Keep `EDU-ERR-01` APPROVED / DEFERRED, REC-25 blocked, LR-D04B deferred, and Vision, Voice, School-Focused mode, archive retrieval, and other frozen/deferred capability tracks out of this transition.

---

## Critical references

- `AGENTS.md`
- `docs/PROJECT_REFERENCE.md`
- `docs/LEARNING_INTELLIGENCE_SPEC.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/SUBJECT_SCOPE_POLICY.md`
- `docs/SUBJ_01_IMPLEMENTATION_SPEC.md`
- `docs/FULL_SYSTEM_ACCEPTANCE_EXECUTION_SPEC.md`
- `TASKS.md`
