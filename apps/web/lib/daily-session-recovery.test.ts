import assert from "node:assert/strict";
import test from "node:test";

import {
  isNonResumableDailyOpenResponse,
  isStaleDailyTurnResponse,
  mergeDailySessionMessages,
  openDailySessionWithSingleReplacement,
} from "./daily-session-recovery";
import * as dailySessionRecovery from "./daily-session-recovery";
import { buildDailySourceSubmission } from "./daily-source";

test("only stale Daily lifecycle responses request replacement", () => {
  assert.equal(isStaleDailyTurnResponse(404, {}), true);
  assert.equal(isStaleDailyTurnResponse(409, { code: "DAILY_SESSION_NOT_RESUMABLE" }), true);
  assert.equal(isStaleDailyTurnResponse(409, { code: "FOREGROUND_TUTOR_BUSY" }), false);
  assert.equal(isStaleDailyTurnResponse(500, {}), false);
  assert.equal(isNonResumableDailyOpenResponse(404, {}), false);
});

test("stale open converges through exactly one replacement request", async () => {
  const requests: Array<Record<string, unknown>> = [];
  const responses = [
    { status: 409, payload: { code: "DAILY_SESSION_NOT_RESUMABLE" } },
    { status: 404, payload: {} },
  ];
  const resolved = await openDailySessionWithSingleReplacement(
    { learning_session_id: "expired" },
    async (request) => {
      requests.push(request);
      return responses[requests.length - 1];
    },
    async (response) => isNonResumableDailyOpenResponse(response.status, response.payload),
  );
  assert.equal(resolved.replaced, true);
  assert.equal(resolved.result.status, 404);
  assert.deepEqual(requests, [
    { learning_session_id: "expired" },
    { replacement_for_session_id: "expired" },
  ]);
});

test("a replayed pending Canvas interaction still resumes its exact Tutor stream", () => {
  const decide = (dailySessionRecovery as Record<string, unknown>)["shouldStartCanvasTutorStream"];
  assert.equal(typeof decide, "function");
  const shouldStart = decide as (result: Record<string, unknown>) => boolean;
  assert.equal(shouldStart({
    replayed: true,
    student_interaction_id: "interaction-1",
    student_interaction_status: "PENDING",
  }), true);
  assert.equal(shouldStart({
    replayed: true,
    student_interaction_id: "interaction-1",
    student_interaction_status: "RUNNING",
  }), false);
  assert.equal(shouldStart({
    replayed: false,
    student_interaction_id: "interaction-1",
    student_interaction_status: "COMPLETED",
  }), false);
});

test("replacement rebind keeps old source historical and preserves a local unsent file", () => {
  const rebind = (dailySessionRecovery as Record<string, unknown>)["rebindRecoveredDailySession"];
  assert.equal(typeof rebind, "function");
  const applyRebind = rebind as (input: Record<string, unknown>) => Record<string, unknown>;
  const oldSource = { id: "old-source", learning_session_id: "old-session" };
  const selectedFile = new File(["local-draft"], "unsent.png", { type: "image/png" });
  const result = applyRebind({
    preservedMessages: [{ id: "old-message", role: "student", source_asset: oldSource }],
    replacement: { learning_session_id: "replacement", messages: [] },
    selectedSource: selectedFile,
  });

  assert.deepEqual((result.session as { messages: unknown[] }).messages, [
    { id: "old-message", role: "student", source_asset: oldSource },
  ]);
  assert.equal(result.activeSource, null);
  assert.equal(result.selectedSource, selectedFile);
  assert.equal((result.session as { learning_session_id: string }).learning_session_id, "replacement");
  const submission = buildDailySourceSubmission({
    content: "new question",
    file: result.selectedSource as File,
    activeSourceId: (result.activeSource as { id?: string } | null)?.id ?? null,
  });
  assert.equal(submission.form.get("source"), selectedFile);
  assert.equal(submission.form.get("source_asset_id"), null);
});

test("an unknown initial URL reference is not converted into implicit session creation", async () => {
  const requests: Array<Record<string, unknown>> = [];
  const resolved = await openDailySessionWithSingleReplacement(
    { learning_session_id: "unknown" },
    async (request) => {
      requests.push(request);
      return { status: 404, payload: {} };
    },
    async (response) => isNonResumableDailyOpenResponse(response.status, response.payload),
  );
  assert.equal(resolved.replaced, false);
  assert.deepEqual(requests, [{ learning_session_id: "unknown" }]);
});

test("replacement preserves rendered history and de-duplicates server overlap", () => {
  const oldMessages = [{ id: "old-student", content: "draft attempt" }, { id: "shared", content: "old copy" }];
  const replacement = [{ id: "shared", content: "server copy" }, { id: "new-tutor", content: "ready" }];
  assert.deepEqual(mergeDailySessionMessages(oldMessages, replacement), [
    ...oldMessages,
    replacement[1],
  ]);
});
