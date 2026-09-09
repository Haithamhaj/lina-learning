# Lina product reference

## Authority and purpose

This is the durable product reference. It owns product purpose, boundaries, and cross-domain decisions. `LEARNING_INTELLIGENCE_SPEC.md` owns Intelligence semantics, `CHILD_SAFETY_POLICY.md` owns Safety policy, and `IMPLEMENTATION_PLAN.md` owns technical architecture.

## Product promise

Lina is a personal learning companion for Lina, initially oriented around Grade 5. The Tutor responds to the current question naturally and safely. It uses available grounding and evidence-informed memory to improve help over time without turning a child into a score, diagnosis, or permanent label.

The current question is authoritative. Tutor availability is independent of curriculum/book availability. Books, trusted references, and Student-captured work are grounding sources, not Teaching Authority.

## Durable boundaries

- Raw messages, original Student work, and source provenance are authoritative and rebuildable.
- A Learning Thread is the session-local contiguous conversation Segment; there is no third Thread entity. Durable conversation topics are optional Grade-scoped navigation metadata, never Intelligence or Safety authority.
- Candidate metadata is provisional. Session-authorized Evidence is distinct from Current State, Pattern, Card, and derived mastery/confidence views.
- Current behavior outranks historical personalization. Patterns are priors, never commands.
- TeachingMode, TeachingStrategy, TeachingMethod, conversation classification, safety, and curriculum semantics remain separate concerns.
- The primary Tutor call semantically determines the turn-level mode, strategy, method, and relevant prior-method relation. Deterministic code validates canonical values, applies policy, manages persistence/lineage, and never substitutes keyword routing.
- Selecting a teaching method is not evidence of effectiveness. Only an observable Lina outcome can support or challenge strategy effectiveness.

## Safety, ownership, and multimodal learning

Child safety is an explicit runtime policy, not a prompt-only behavior. Parent Learning Boundaries can restrict further but cannot weaken the baseline. Student ownership and privacy are enforced independently of a browser-supplied identity.

Text, voice, image, PDF, and DOCX sources may support one normal Tutor interaction. The original Student source remains private authority; AI-derived annotations or reconstructions are separate, derived artifacts. Safety applies before Tutor or Canvas work; blocked inputs create no learning-derived conclusion.

## Studio and Canvas

Chat/Tutor is the language and reasoning authority. Canvas is a bounded educational representation surface that may clarify a Tutor-selected method; it must not block conversation or become a competing teaching agent. Chat, Canvas, and continuation share the same Tutor context.

Studio’s primary product subjects are MATH, SCIENCE, ENGLISH, and ARABIC. General/unknown conversation remains allowed in Chat. Current accepted Math representation includes a Cartesian plane from `-10` to `10` on each axis. See `domains/STUDIO.md` and `domains/EDUCATIONAL_VISUALS.md`.

## Learning Intelligence

The learning loop is raw interaction → completed Segment review → session-authorized Event/Evidence → Current State/Patterns → compact Card → relevant later support. It is evidence-grounded, versioned, traceable, and rebuildable. The Card is a runtime projection, not source truth. See `LEARNING_INTELLIGENCE_SPEC.md`.

## Architecture decisions

Lina is a modular monolith: web client, FastAPI API, PostgreSQL/pgvector, object storage where needed, worker, and Model Gateway. Do not add a new agent framework, vector database, microservice, or core infrastructure service without demonstrated need and Product Owner approval.

## Current product reality and limits

Primary Tutor, Intelligence foundations, Personal Facts/Core Profile, optional RAG, Voice/STT, Vision image/PDF/DOCX sources, multimodal Safety, durable Studio runtime, Canvas Specialist, production Canvas patterns, and Daily Student surface are implemented in the accepted baseline. Authenticated Daily acceptance, recurring real Lina use, and longitudinal calibration are not yet proven merely by that implementation.
