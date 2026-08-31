# Daily-Use Lina Release 1 — Approved Decision Register

**Status:** Product Owner approved on 2026-08-31  
**Purpose:** Compact decision register for product truths introduced after `DOC-SYNC-01` acceptance and the RL-01 Current Reality Audit. This register supplements `PROJECT_REFERENCE.md` until a later routine documentation consolidation; it does not change Learning Intelligence semantics.

## Decisions

1. Existing historical interaction/database data is experimental/test material and will not be imported as Lina's longitudinal history. Daily-Use Release 1 uses one fresh current-schema application database; test/validation data and Lina data may coexist in that database under different Student identities.
2. Lina's real longitudinal baseline is **Student-scoped**, not database-scoped: when Lina begins real use, her own Student identity must have zero prior Sessions, Messages, Segments, Personal Facts, Learning Events/Evidence, Current State, Patterns, Decision Views, and other Student-owned learning history.
3. Test/validation Student identities may be used in the same application database for RL-01C/RL-01D and later verification. Their data must never enter Lina's conversation context, Personal Facts, Learner Intelligence, assets, or authorization scope. Cross-Student isolation is a Criticality-5 launch invariant.
4. Personal Facts are a separate Student-asserted context layer, distinct from Student Core Profile and Learning Intelligence.
5. Personal Facts come from what the Student tells the system about herself/her world; Parent claims do not automatically become Student Personal Facts.
6. Personal Facts may evolve through repeated support, contradiction, invalidation, and supersession with source-message/time lineage.
7. Personal Facts do not create Learning Evidence, personality/psychology conclusions, intelligence labels, or learning-style labels.
8. Parent may inspect stored Personal Facts.
9. Facts × Learning Parent insight analysis is future/data-dependent; no talent/ML architecture is approved now.
10. Renderer-first is the primary learning-visual strategy: React/SVG, Motion, JSXGraph, React Konva, MathLive as the approved baseline direction.
11. Image generation is optional/deferred and illustrative; it is not the default teaching renderer.
12. Student work images preserve the original as raw source. Derived annotation on the original is the default visual feedback path; clean reconstruction is fallback when annotation is insufficient.
13. Daily-Use Lina frontend improvement is launch scope. The target is playful + intelligent + polished + personal, not preschool/corporate.
14. Frontend reuse must be selective; ThreeUI/Three.js is a selective visual source/capability, not app architecture.
15. Initial Voice is Audio → STT → transcript → normal Tutor. No speech-to-speech requirement for Release 1; raw audio is not retained after successful STT under current policy.
16. Vision/photo input is promoted into the launch sequence after the foundation/frontend gates.
17. Current native Docling + PostgreSQL/pgvector hybrid RAG remains the launch baseline. Alternative RAG approaches require measured post-launch evaluation.
18. AI capabilities continue behind Model Gateway; OpenAI is a current operational provider, not permanent product architecture.
19. Replit may be used as a private daily-use environment after fit/proof; it is not architecture and the old Phase-0 app is not the source baseline.
20. Daily-Use Release 1 executes one task at a time according to `project-state/DAILY_USE_RELEASE_TASKS.md`.
