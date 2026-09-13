# Canvas development review

Status: local engineering implementation verified; reviewer accuracy remains unaccepted. Product Owner requested an independent development archive and an AI reviewer, and explicitly authorized sending the prepared evidence to OpenAI on 2026-09-13. Branch publication is authorized; no merge or deployment.

## Purpose and boundary

This module reviews Canvas engineering quality, separately from student personalization. It writes only `canvas_development_reviews` and the normal `AIExecution` operational ledger. It never writes learner Evidence, State, Patterns, Personal Facts or Intelligence Cards, and is not retrieved by the normal Tutor. Reports are recommendations, not release approval, artifact promotion or automatic source edits.

Existing persisted Specialist runs form the paginated index, including failures. This version does not index every chat-only or legacy non-Specialist Canvas experience. Capture and model analysis are explicit operator operations, with no student runtime hook or extra model call per student action. Failures cannot interrupt the student's conversation.

## What is preserved

Each capture creates a new independently identified row with operator attribution, run/runtime/student/session ownership, capture time, schema version, SHA-256 evidence digest and status. A new capture and analysis for the same Canvas run creates a new record; completed reports are not overwritten, so comparisons remain possible. Evidence includes:

- The admitted Canvas brief, run outcome and bounded operational diagnostics.
- Accepted Scene/version, immutable Build reference/digests, parameters and canonical Manifest, resolved through existing owner/digest checks. Artifact Version lineage is recorded where the Scene uses a reusable version. Generated source is resolved from its immutable Build only while previewing or asking the reviewer; it is not copied into the review record.
- Up to 100 recorded Scene events, with bounded technical payloads; up to 100 Tutor-continuation status records linked to captured Scene events and up to 100 run-linked model executions with usage/cost/failure metadata.
- Up to six new screenshots and diagnostics from the existing isolated production preview at desktop widths 640/960. These are synthetic reproductions, **not recordings of the student's actual screen or an exact replay of the student session**.
- Explicit coverage limits, missing evidence and truncation. Typed/image blocks and additional custom blocks are not visually reproduced by this version. Failed builds without an accepted Scene cannot acquire screenshots retrospectively.

The bounded evidence pack, including inline PNG images, is stored in the same private PostgreSQL review row (maximum 4 MB). Existing ObjectStorage is read through the immutable Build resolver; this module creates no separate object copies or public image URLs. This keeps deletion lifecycle simple and prevents orphan review files. Complete raw conversations, original uploads and learner personalization are not copied. Technical metadata can contain model-generated text and remains untrusted.

The run ownership foreign key also governs review deletion: authorized deletion of the parent run cascades to its review pack and report. No automatic retention timer or independent data-deletion authorization is introduced. Exported local files require the same private handling and explicit cleanup as other operator evidence exports. The migration refuses downgrade while review records exist.

## AI review

One explicit analysis claims a READY capture, commits that claim, then calls the configured model through the dedicated `canvas_development_review` Model Gateway task. No runtime locks are held across the browser or model operation. Model provider/model/usage/latency/cost/failure remain in the existing ledger. Images are bounded inline PNGs; external image URLs are rejected. The provider request uses `store=false`.

The structured Arabic report distinguishes observed facts, inferences and required verification. Each finding requires a known evidence reference, severity, recommendation and verification method. Unknown evidence references reject the report; capture limitations are always appended. Reference validation proves that a source exists, not that the model interpreted it correctly. Student benefit and mastery are not inferred from successful rendering, clicks or model self-review.

READY -> RUNNING -> COMPLETED/FAILED is a one-shot analysis lifecycle. Provider failures remain recorded; retries require a new capture. If an operator process is forcibly killed, CAPTURING/RUNNING may remain visible; there is no automatic retry or duplicate billing. Operators may create a new capture after inspecting the original execution ledger. Automated recovery and a web dashboard are outside this slice.

## Operator workflow

Run from the authoritative checkout with the configured Python environment and explicit database/storage/model settings. This CLI assumes a trusted developer operating with database credentials. `--student-id` narrows ownership but is not a substitute for authentication. Parent access does not confer developer access. There is no public HTTP endpoint.

```sh
python -m scripts.review_canvas_development list --student-id STUDENT_UUID --env-file ENV_FILE
python -m scripts.review_canvas_development reviews --student-id STUDENT_UUID --run-id RUN_UUID --env-file ENV_FILE
python -m scripts.review_canvas_development capture --student-id STUDENT_UUID --run-id RUN_UUID --requested-by OPERATOR --env-file ENV_FILE
python -m scripts.review_canvas_development analyze --student-id STUDENT_UUID --review-id REVIEW_UUID --live --env-file ENV_FILE
python -m scripts.review_canvas_development show --student-id STUDENT_UUID --review-id REVIEW_UUID --env-file ENV_FILE
python -m scripts.review_canvas_development evidence --student-id STUDENT_UUID --review-id REVIEW_UUID --env-file ENV_FILE
```

`list --offset N` pages the existing Canvas-run index. `reviews --run-id RUN_UUID` lists every independent prior review for one experience; omit `--run-id` to list the developer-visible history for the selected student. `capture --no-preview` deliberately omits browser images and records that limitation. `evidence` returns the complete private pack for inspection/export; `show` returns the stored report, reviewer model/version metadata and digest without image bytes. `--requested-by` is attribution, not a verified role. Never expose this CLI behind a student or parent endpoint without a separate developer authorization layer.

## Actual proof and limits

On 2026-09-13, an existing disposable reflection run produced a READY pack containing 17 evidence items and six reproduction images. Review `5c73a0f8-4238-4998-8a51-8d923ba2a9c9` completed with OpenAI `gpt-5.6-luna`: 14,297 ms, estimated $0.013630. Learning messages (382), learning Evidence (0), Studio events (218), Scenes (58) and Builds (54) had unchanged counts before capture and after analysis. The independent module does not update those models.

**Human assessment of this first report:** the AI correctly separated recorded SELECT from synthetic MOVE and surfaced historical readability issues. It missed the known unequal x/y scale behind the “square grid” label (536 horizontal versus 260 vertical drawing units for the same numeric range). This is a recorded reviewer false negative. Successful report generation is not proof that the reviewer reliably finds errors. No learning-effectiveness or production-release conclusion is claimed.

Private proof artifacts: `output/canvas-production-hardening/development-review-local.json` and `development-review-live.json`. The saved database case retains evidence IDs so findings can be checked against their sources. No second model retry was used to hide the false negative.

## Verification closure

Focused review/provider tests: 39 passed. Full integrated regression after the final review-history, source-reference and schema/preflight changes: 1426 passed, 12 skipped (68.95 s) on isolated PostgreSQL 55438. Repository truth and `git diff --check` passed. No frontend change requires a new UI build.

The production migration was applied only to isolated regression database 55438 and preserved disposable proof database 55434. Production deployment and a developer web UI are not part of this closure. The evidence/archive/report mechanism is verified; semantic reviewer reliability and student learning benefit remain separate open gates.
