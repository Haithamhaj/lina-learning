# CS-02 — Complete Visual Toolbelt — Implementation Record

**Status:** DONE / ACCEPTED
**Prepared:** 2026-09-07
**Execution branch:** `codex/ctx-03`
**Implementation baseline:** `06d6c0852b36a98b4a58a3c9156f8105bdfd9916`
**Purpose:** Install and prove the approved visual Toolbelt through isolated,
application-owned adapters without production-enabling a learning capability.

## 1. Pre-implementation governance correction

`AGENTS.md` contained stale CS-01-current/CS-02-blocked wording after accepted
CS-01 closure. Before package or implementation work, it was narrowly aligned
to the accepted current execution authority: CS-01 is DONE / ACCEPTED, CS-02
is the sole READY task, and CS-03 through CS-07 remain BLOCKED. No architectural
rule, authority boundary, or historical record was changed.

## 2. Approved scope and protected boundaries

Approved packages: `motion`, `react-konva@18` with `konva`, `jsxgraph`, and
`mathlive`; React/DOM/SVG remains the existing baseline. This task creates only
client/lazy, application-owned Toolbelt adapters and isolated review proofs.

Protected and out of scope: Primary Tutor authority; `workspace_intent-v1`;
Studio routing/protocol/Scene/Event/Snapshot state; ProcessView; ModelTask,
Gateway, Worker, Specialist lifecycle; database/schema/migrations; Learning
Evidence/Personal Facts/Learner Intelligence; generated images/3D; generic
Artifact Engine; and all CS-03+ work.

## 3. Pre-install dependency fit decisions

| Engine | Decision | Fit rationale |
|---|---|---|
| Motion | ADOPT | Open-source package, React 18/App Router client support, SVG/DOM semantic animation and reduced-motion APIs. No Motion+ or token/private registry use. |
| React Konva + Konva | ADOPT | `react-konva@18` is the React-18-compatible package line. Keep it client-only behind a local adapter and return semantic placement rather than raw pixels. |
| JSXGraph | ADOPT | Browser board supports bounded mathematical construction. Local adapter owns CSS, board init/options and `freeBoard` cleanup. |
| MathLive | ADOPT | Web component supports bounded controlled value handoff. Local client adapter owns registration, fonts/sounds configuration and avoids CDN coupling. |

Exact resolved versions, final fit evidence, changed paths, verification,
browser proof, scope review, and independent-review result will be recorded
before Product Owner review.

## 4. Expected paths and verification plan

Expected changes are the web manifest/lockfile, a small
`apps/web/lib/studio/visual-toolbelt/` boundary, isolated review proof surface,
focused tests, sanitized CS-02 review evidence, this record, and the narrow
`AGENTS.md` correction above. Planned evidence: dependency tree/lockfile,
focused tests, `npm run typecheck`, `npm run build`, relevant Studio/Process
regressions, Chromium proof for each engine, and `git diff --check`.

## 5. Evidence status before implementation

| Evidence category | Status |
|---|---|
| Static/contract review | PLANNED |
| Unit/contract tests | NOT RUN |
| Production build/typecheck | NOT RUN |
| Browser proof | NOT RUN |
| Model/Luna | NOT APPLICABLE — no model path is added |
| PostgreSQL product evidence | NOT APPLICABLE — no persistence path is changed |

## 6. Implementation decisions

Installed Motion 13.2.0, react-konva 18.2.16, Konva 10.3.3, JSXGraph 1.13.3,
and MathLive 0.110.0. Each proof is isolated under
`apps/web/lib/studio/visual-toolbelt/`; Konva/JSXGraph/MathLive are loaded by a
review-only `next/dynamic(..., { ssr: false })` surface. JSXGraph CSS and
MathLive fonts are locally served under `apps/web/public/visual-toolbelt/` and
`apps/web/public/mathlive/fonts/`; MathLive sounds are disabled.

## 7. Actual changed paths

`AGENTS.md`; `apps/web/package.json`; `package-lock.json`; local public CSS and
font assets; `apps/web/lib/studio/visual-toolbelt/`; isolated
`apps/web/app/studio/visual-toolbelt-review/page.tsx`; focused node contract
test; and this record.

## 8. Verification results

- `node --test apps/web/tests/cs02-visual-toolbelt-contract.mjs`: 2 passed,
  0 failed, 0 skipped (rerun after final lifecycle corrections).
- `PYTHONPATH=. uv run --with-requirements apps/api/requirements.txt --with pytest pytest -q tests/test_process_visual_awareness.py`:
  19 passed, 0 failed, 0 skipped.
- `npm run typecheck`: passed.
- `npm run build`: passed after correcting JSXGraph's non-exported CSS subpath
  by locally serving the installed CSS; `/student/daily` remained 151 kB and
  the isolated review route was 42.3 kB.
- Chromium review route rendered Motion, Konva, JSXGraph, and MathLive. Normal
  Motion rendered the relation trace; emulated `prefers-reduced-motion: reduce`
  retained the same relation endpoints. The Motion status was made
  client-mounted to eliminate the reduced-motion hydration mismatch.
- MathLive keyboard input updated the controlled browser value (`x^2+1y^2+2`)
  without recreating the field after each input; its callback is stabilized in
  the isolated review page. Its 20 font requests were local `/mathlive/fonts/*`
  resources, and no MathLive font, sound, or CDN request was observed. Sounds
  are explicitly disabled.
- Navigation from the proof route to `/studio/process-sequence-review` and back
  remounted all proof surfaces. JSXGraph's bounded RTL-surrounded/LTR board
  rendered and its adapter performs `freeBoard` cleanup on unmount. The review
  route had no engine console error; a local-development `icon.svg` 404 and the
  pre-existing Clerk development-key warning remain separate environment/app
  noise. Production build passed.
- `git diff --check`: passed after the final record update.

## 9. Independent review

Independent read-only diff review initially found one Important issue: the
inline MathLive callback changed identity on every parent update and recreated
the field. It was corrected by stabilizing both review-page callbacks with
`useCallback`; focused contract/typecheck/build and browser keyboard evidence
were rerun.

Product Owner final diff review then found one Important JSXGraph lifecycle
issue: initialization used the dynamically imported module API while cleanup
depended on `window.JXG`. The proof now retains the imported API in the effect,
calls `JXG.JSXGraph.freeBoard(board.current)` only when that API and a board
exist, then clears both references. The async inactive guard remains, and the
unnecessary separate `removeAllObjects()` call was removed. The focused
contract now rejects `window.JXG` and requires the retained imported-API
`freeBoard` lifecycle. Post-fix focused test, typecheck, production build, two
browser navigate-away/remount cycles, and `git diff --check` passed. Final
classification: Critical 0, Important 0, Minor 0.

## 10. Known unverified evidence / blockers

Trusted/emulated touch drag was not available through the repository's
Playwright CLI command set. Existing typed Renderer Host/protocol/controller
and `/student/daily` web tests could not be executed with a repository-declared
TypeScript test runner; no runner was added. The Process visual-awareness
regression was executed above. No production route, Tutor, Specialist execution,
persistence, or academic validation behavior changed.

## 11. Scope review

No CS-03 structures, Tutor/WorkspaceIntent/Studio routing/ProcessView,
database/schema, ModelTask/Gateway/Worker, or production learning capability
was modified.

## 12. Product Owner disposition

**DONE / ACCEPTED.** Product Owner accepted CS-02 with Critical 0, Important 0
and Minor 0. The Product Owner-found JSXGraph lifecycle issue remains recorded
above as found and corrected. CS-03 is the next READY task; it is not executed
by this closure.
