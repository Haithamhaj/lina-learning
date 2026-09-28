import assert from "node:assert/strict";
import test from "node:test";

import {
  canvasLifecycleNotice,
  claimCanvasLifecycleNotice,
  conversationNoticeDirection,
  readSeenCanvasNotices,
  saveSeenCanvasNotices,
} from "./composition-notices.ts";
import { shouldReplaceCompositionView, type CompositionView } from "./composition-recovery.ts";
import { dailyPresentationCopy } from "../daily-presentation-copy.ts";

const pending = {
  observed_at: "2026-09-28T00:00:00Z",
  run_id: "run-1",
  run_created_at: "2026-09-28T00:00:00Z",
  run_status: "PENDING",
  scene_ready: false,
};

test("English UI uses Arabic lifecycle copy for an Arabic Tutor conversation", () => {
  const direction = conversationNoticeDirection([
    { role: "student", content: "Can we see the water cycle?" },
    { role: "tutor", content: "سأجهّز لكِ رسماً لدورة الماء، ثم نتتبّع الأسهم معاً." },
  ]);
  assert.equal(direction, "rtl");
  assert.match(dailyPresentationCopy(direction ?? "ltr").canvas.lifecycle.preparing, /أجهّز/);
});

test("Arabic UI uses English lifecycle copy for an English Tutor conversation", () => {
  const direction = conversationNoticeDirection([
    { role: "student", content: "هل يمكنك شرح الرسم؟" },
    { role: "tutor", content: "I’ll prepare a visual, then we can trace the arrows together." },
  ]);
  assert.equal(direction, "ltr");
  assert.match(dailyPresentationCopy(direction ?? "rtl").canvas.lifecycle.ready, /ready in Canvas/);
});

test("neutral or empty conversation text preserves the UI-language fallback", () => {
  const direction = conversationNoticeDirection([
    { role: "student", content: "21 ÷ 3 = ?" },
    { role: "tutor", content: "" },
  ]);
  assert.equal(direction, null);
  assert.match(dailyPresentationCopy(direction ?? "ltr").canvas.lifecycle.preparing, /preparing/);
  assert.match(dailyPresentationCopy(direction ?? "rtl").canvas.lifecycle.preparing, /أجهّز/);
});

test("a clear current Student language outranks older Tutor text while the next reply is pending", () => {
  assert.equal(conversationNoticeDirection([
    { role: "tutor", content: "Let’s continue with the diagram." },
    { role: "student", content: "اشرح لي الرسم الجديد." },
    { role: "tutor", content: "" },
  ]), "rtl");
});

test("start and in-flight polls produce one preparation milestone without a ready claim", () => {
  const started = canvasLifecycleNotice(pending);
  const running = canvasLifecycleNotice({ ...pending, observed_at: "2026-09-28T00:00:01Z", run_status: "RUNNING" });
  assert.equal(started?.kind, "preparing");
  assert.equal(started?.id, running?.id);
});

test("ready requires authoritative scene_ready rather than COMPLETED alone", () => {
  const completed = { ...pending, run_status: "COMPLETED" };
  assert.equal(canvasLifecycleNotice(completed), null);
  assert.equal(canvasLifecycleNotice({ ...completed, scene_ready: true })?.id, "run-1:ready");
});

test("each failure outcome is truthful and a terminal milestone is emitted once", () => {
  for (const status of ["FAILED", "REJECTED", "CANCELLED"] as const) {
    const notice = canvasLifecycleNotice({ ...pending, run_status: status });
    assert.equal(notice?.kind, status.toLowerCase());
    assert.equal(notice?.id, "run-1:terminal");
  }
});

test("session storage prevents a second ready notice after polling or remount", () => {
  const data = new Map<string, string>();
  const storage = { getItem: (key: string) => data.get(key) ?? null, setItem: (key: string, value: string) => { data.set(key, value); } };
  const notice = canvasLifecycleNotice({ ...pending, run_status: "COMPLETED", scene_ready: true })!;
  const first = readSeenCanvasNotices(storage, "session-1");
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "COMPLETED", scene_ready: true }, first)?.id, notice.id);
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "COMPLETED", scene_ready: true, observed_at: "2026-09-28T00:00:30Z" }, first), null);
  saveSeenCanvasNotices(storage, "session-1", first);
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "COMPLETED", scene_ready: true }, readSeenCanvasNotices(storage, "session-1")), null);
  assert.equal(readSeenCanvasNotices(storage, "session-2").has(notice.id), false);
});

test("retained latest view rejects a stale older run after the Scene loads", () => {
  const newer: CompositionView = { ...pending, observed_at: "2026-09-28T00:02:00Z", run_id: "run-2", run_created_at: "2026-09-28T00:02:00Z", run_status: "COMPLETED", scene_ready: true };
  const older: CompositionView = { ...pending, observed_at: "2026-09-28T00:03:00Z", run_status: "COMPLETED", scene_ready: true };
  assert.equal(shouldReplaceCompositionView(newer, older), false);
  assert.equal(shouldReplaceCompositionView(older, newer), true);
});

test("storage denial keeps lifecycle notices available in memory", () => {
  const seen = readSeenCanvasNotices(null, "session-1");
  assert.equal(claimCanvasLifecycleNotice(pending, seen)?.kind, "preparing");
  saveSeenCanvasNotices(null, "session-1", seen);
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "RUNNING" }, seen), null);
});

test("one run moves from preparation to ready, then a newer run can fail", () => {
  const seen = new Set<string>();
  const first = claimCanvasLifecycleNotice(pending, seen);
  assert.equal(first?.id, "run-1:start");
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "RUNNING" }, seen), null);
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "COMPLETED", scene_ready: false }, seen), null);
  assert.equal(claimCanvasLifecycleNotice({ ...pending, run_status: "COMPLETED", scene_ready: true }, seen)?.id, "run-1:ready");
  const newer = { ...pending, run_id: "run-2", run_created_at: "2026-09-28T00:01:00Z" };
  assert.equal(claimCanvasLifecycleNotice(newer, seen)?.id, "run-2:start");
  assert.equal(claimCanvasLifecycleNotice({ ...newer, run_status: "FAILED" }, seen)?.id, "run-2:terminal");
  assert.equal(claimCanvasLifecycleNotice({ ...newer, run_status: "FAILED" }, seen), null);
});
