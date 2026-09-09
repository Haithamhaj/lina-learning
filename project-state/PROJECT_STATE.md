# Lina Personal Learning System — Project State

## Current Goal

Practical validation of the complete multimodal Daily Tutor → Canvas → Tutor learning experience.

## Current Reality

- The Primary Tutor runtime exists.
- Daily text, microphone transcription, and Student source input now converge on
  the same Primary Tutor. VISION-01 preserves immutable private image/PDF/DOCX
  originals, exact Student-message and AI-execution lineage, same-source
  follow-ups, and exact text-only behavior when no source is active. Bounded real
  Luna image/PDF/follow-up proof passed with exactly three Tutor calls.
- VISION-01S closes the multimodal Child Safety gap before the Primary Tutor.
  Owned images use their actual bytes; PDFs use transient extracted text and
  rendered pages; DOCX uses transient XML text and supported embedded images.
  `omni-moderation-latest` supplies signals, Lina's existing policy remains the
  decision authority, inspection failure fails closed, and compact audits retain
  no source bytes, raw provider response, or score dump. Live synthetic proof
  passed with four moderation calls, three allowed Tutor calls, and zero Tutor or
  learning-derived writes for the blocked image.
- DOCX Tutor comprehension is deterministic: the Safety boundary and Tutor
  adapter share one transient ordered-paragraph extractor, and the same Tutor
  request receives that text plus the immutable original file. A one-call live
  Luna proof read the DOCX-only `18 cm` fact; extracted text was not persisted.
- Studio durable state and runtime exist.
- Canvas Specialist execution exists.
- A production Process sequence/cycle exists.
- Semantic Process motion V2 exists.
- CS-07 visual Toolbelt primitives are hardened: controlled Motion focus, Konva
  placement, exact JSXGraph coordinates and MathLive input; isolated Chrome proof
  passed. Authenticated Daily remains unverified (Clerk secret unavailable).
- Canvas supports four production patterns through one runtime: Process
  (sequence/cycle), spatial manipulation, mathematical construction and math
  expression. The Primary Tutor emits a strict semantic order, the Canvas
  Specialist composes only supported meaning, and the application selects an
  exact local renderer. All four use server-owned Scene/Event/Snapshot state in
  the Daily Renderer Host.
- V2 PostgreSQL lifecycle and replay proof exists.
- Canvas interaction returns to the same Primary Tutor.
- Real Arabic source validation now proves coordinate comprehension and the
  full Chat → bounded Canvas → interaction → same-Tutor path. Workspace
  capability selection keeps the four Studio subjects separate from Broad
  Subject classification, advertises exact pattern bounds, and no longer loses
  a valid MATH/SCIENCE composition merely because the subject becomes known.
  Dense low-clarity handwriting remains source-quality limited: Luna asks for a
  clearer crop instead of inventing unreadable mathematical text.
- Broader authenticated end-user quality and usability still need practical
  validation.

## Protected Areas

1. Child Safety baseline.
2. Authentication, privacy, Student ownership, and data isolation.
3. Learning Evidence / Learning Intelligence write authority and meaning.
4. Destructive database, schema, or data-migration behavior.
5. Irreversible external actions, including deployment, paid effects, and
   destructive remote operations.

## Current Risks

- Authenticated Daily browser validation is blocked by absent local Clerk
  configuration; exact production Renderer Host validation has passed in an
  authentication-independent Chrome harness.
- The real Student experience may expose usability defects.

## Next Practical Goal

Provide local Clerk configuration, then run an authenticated disposable-Student
Daily journey covering text, voice, image/PDF/DOCX source history, and Canvas;
fix any experience defects that appear in real use.
