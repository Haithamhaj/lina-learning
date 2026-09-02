import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../../../", import.meta.url);
const hook = readFileSync(
  new URL("apps/web/components/daily-student/use-daily-tutor-session.ts", root),
  "utf8",
);
const chat = readFileSync(
  new URL("apps/web/components/daily-student/daily-learning-chat.tsx", root),
  "utf8",
);

test("FE-02-STREAM-01 and FE-02-SSE-01 preserve the authenticated server-owned Tutor stream", () => {
  assert.match(hook, /useAuth/);
  assert.match(hook, /\/v1\/student\/math\/session/);
  assert.match(hook, /\/turn\/stream/);
  assert.match(hook, /Authorization: `Bearer \$\{token\}`/);
  assert.match(hook, /type === "delta"/);
  assert.match(hook, /type === "turn"/);
  assert.match(hook, /guided_check_id/);
  assert.match(hook, /terminal_turn_received/);
  assert.match(hook, /setState\("ready"\)/);
  assert.doesNotMatch(hook, /useChat|UIMessage|assistant-ui|ai-sdk/i);
  assert.doesNotMatch(hook, /new EventSource|WebSocket|eventSource/i);
});

test("FE-02-DATA-01 uses private lifecycle tracing and the accepted incomplete-stream rollback", () => {
  assert.match(hook, /createTutorStreamLifecycleTrace/);
  assert.match(hook, /finalizeTutorStream/);
  assert.match(hook, /stream_incomplete/);
  assert.match(hook, /terminalTurnReceived/);
  assert.match(hook, /stream_eof/);
  assert.match(hook, /ui_ready/);
  assert.doesNotMatch(hook, /localStorage/);
});

test("FE-02-STREAM-01 never replays submitted learner content after an incomplete stream", () => {
  assert.match(hook, /finalizeTutorStream/);
  assert.match(hook, /\{ id: studentId, role: "student", content/);
  assert.match(chat, /retryOpening/);
  assert.match(chat, /Your message is still here/);
  assert.doesNotMatch(chat, /retryContent/);
  assert.doesNotMatch(chat, /send\(retryContent\)/);
});
