# FE-02 Prototype Preservation Manifest

## Status

PROTOTYPE / NON-AUTHORITATIVE / NOT ACCEPTED / NOT PRODUCTION ARCHITECTURE

## Preserved from

- source branch: `codex/ctx-03`
- source parent HEAD: `059ff3aa6bfb983507470f484596bf05eae3b9b3`
- source worktree: `/Users/haitham/development/lina-learning-ctx03`
- preservation date: 2026-09-02

## Purpose

- Preserve the Desktop Chat + Workspace shell and its contract tests.
- Provide recoverable design/code evidence.
- Allow explicit later porting of retained parts.

DO NOT MERGE THIS BRANCH AS THE PRODUCTION STUDIO IMPLEMENTATION.

Future production work may port only explicitly approved pieces such as:

- `/student/daily` route boundary;
- Chat + Workspace desktop composition;
- project-owned Tutor stream-controller patterns;
- provisional/terminal transcript handling;
- accessibility/direction behavior;
- responsive shell concepts.

Prototype-only behavior that must not be promoted automatically:

- Tutor-prose parsing;
- equation-regex extraction;
- message-derived Canvas state;
- browser-local state as Studio authority;
- duplicated Workspace cards;
- assumptions that Canvas waits for terminal Chat;
- absence of durable Event Log/Snapshot/feed.

## Inventory

| Path | Type | Bytes | Lines | SHA-256 |
| --- | --- | ---: | ---: | --- |
| `apps/web/app/student/daily/page.tsx` | Source | 368 | 11 | `d0fdc21ef3894b2691286ec6755934ec6c27019c0549e237c7b333d080785ee8` |
| `apps/web/components/daily-student/daily-learning-chat.tsx` | Source | 8671 | 122 | `7e0adfa55eaf6b6fba1999d6f2307a5312b8afd5013eb2b297dc23506bbf3d8c` |
| `apps/web/components/daily-student/daily-learning-workspace.tsx` | Source | 15393 | 156 | `35273e95d5ebae7233c1e06c015e68cfc7ccbedcef65767fbf58591f1c2ba0a7` |
| `apps/web/components/daily-student/daily-student-app.tsx` | Source | 2311 | 41 | `4f0ea9c91443e00856a0481bfcda5cb1259e05632c04ec92b743abc330c6fc08` |
| `apps/web/components/daily-student/use-daily-tutor-session.ts` | Source | 8471 | 251 | `29fad409914da5c38a125950c00320250429103c494068167144046135a68013` |
| `apps/web/tests/daily-student-stream-contract.test.mjs` | Test | 1878 | 46 | `fbdd68b3f9572c3a8d11f9d23ef6e774fcc7ff266a8c67eb81af4e76130d929f` |
| `apps/web/tests/daily-student-surface-contract.test.mjs` | Test | 3606 | 77 | `fddc6c1263846e5a05a19c8c74eec640ae1ba2bd0e27d1d1d92bd591bcbb348e` |

Each destination SHA-256 was compared with the source worktree and matched.

## Verification

- Focused Node contracts: passed — 7 tests, 0 failures.
- Typecheck: passed — `npm run typecheck`.
- Build: passed — `npm run build`.
- Dependency changes: none.

## Governing reference

The accepted production-intent implementation direction is
`docs/STUDIO_IMPLEMENTATION_PLAN.md`. This prototype branch is archival
evidence only and does not override that governing plan.
