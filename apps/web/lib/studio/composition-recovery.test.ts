import assert from "node:assert/strict";
import test from "node:test";

import {
  canvasElapsedSeconds,
  canvasPresentationState,
  canvasWaitingMotionClass,
  isDailyComposerDisabled,
  shouldRefreshCompositionSnapshot,
  shouldReplaceCompositionView,
  type CompositionView,
} from "./composition-recovery.ts";

const oldPending: CompositionView = { observed_at: "2026-09-16T00:00:00Z", run_id: "run-old", run_created_at: "2026-09-16T00:00:00Z", run_status: "PENDING", scene_ready: false };
const newPending: CompositionView = { observed_at: "2026-09-16T00:01:00Z", run_id: "run-new", run_created_at: "2026-09-16T00:01:00Z", run_status: "PENDING", scene_ready: false };

test("an older composition poll cannot clear a newer pending run", () => {
  assert.equal(shouldReplaceCompositionView(newPending, { observed_at: "2026-09-16T00:00:02Z", run_id: "run-old", run_created_at: "2026-09-16T00:00:00Z", run_status: "COMPLETED", scene_ready: true }), false);
});

test("a newer pending run replaces an older pending run", () => {
  assert.equal(shouldReplaceCompositionView(oldPending, newPending), true);
});

test("same-run lifecycle updates replace the earlier server observation", () => {
  const running = { ...newPending, observed_at: "2026-09-16T00:01:01Z", run_status: "RUNNING" as const };
  const completed = { ...newPending, observed_at: "2026-09-16T00:01:02Z", run_status: "COMPLETED" as const, scene_ready: true };
  assert.equal(shouldReplaceCompositionView(newPending, running), true);
  assert.equal(shouldReplaceCompositionView(running, completed), true);
});

test("a stale same-run observation cannot roll back a settled view", () => {
  const completed = { ...newPending, observed_at: "2026-09-16T00:01:02Z", run_status: "COMPLETED" as const, scene_ready: true };
  assert.equal(shouldReplaceCompositionView(completed, { ...newPending, observed_at: "2026-09-16T00:01:01Z", run_status: "RUNNING" }), false);
});

test("equal creation times for different runs retain the known view", () => {
  assert.equal(shouldReplaceCompositionView(newPending, { ...oldPending, observed_at: "2026-09-16T00:01:02Z", run_created_at: newPending.run_created_at }), false);
});

test("initial PENDING opens the Workspace in a preparing state", () => {
  assert.deepEqual(canvasPresentationState(oldPending, false), {
    showWorkspace: true,
    showWaiting: true,
    showUpdating: false,
    showFailure: false,
    animateWaiting: true,
  });
});

test("RUNNING after reload derives elapsed time from server run_created_at", () => {
  const running = { ...oldPending, run_status: "RUNNING" };

  assert.equal(canvasElapsedSeconds(running.run_created_at, Date.parse("2026-09-16T00:00:18Z")), 18);
  assert.equal(canvasPresentationState(running, false).showWaiting, true);
});

test("an active Scene remains visible while a newer run is preparing", () => {
  assert.deepEqual(canvasPresentationState(newPending, true), {
    showWorkspace: true,
    showWaiting: false,
    showUpdating: true,
    showFailure: false,
    animateWaiting: true,
  });
});

test("COMPLETED plus scene_ready requests the authoritative Snapshot", () => {
  assert.equal(shouldRefreshCompositionSnapshot({ ...newPending, run_status: "COMPLETED", scene_ready: true }), true);
  assert.equal(shouldRefreshCompositionSnapshot({ ...newPending, run_status: "COMPLETED", scene_ready: false }), false);
});

test("terminal failure statuses stop waiting and expose a failure state on initial load", () => {
  for (const run_status of ["FAILED", "REJECTED", "CANCELLED"] as const) {
    assert.deepEqual(canvasPresentationState({ ...newPending, run_status }, false), {
      showWorkspace: true,
      showWaiting: false,
      showUpdating: false,
      showFailure: true,
      animateWaiting: false,
    });
  }
});

test("reduced-motion styling disables animation without hiding the waiting state", () => {
  assert.match(canvasWaitingMotionClass, /motion-reduce:animate-none/);
  assert.equal(canvasPresentationState(oldPending, false).showWaiting, true);
});

test("Canvas background work does not disable Chat after the Tutor turn settles", () => {
  assert.equal(isDailyComposerDisabled({ tutorResponding: true, voiceBusy: false }), true);
  assert.equal(isDailyComposerDisabled({ tutorResponding: false, voiceBusy: false }), false);
});
