import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const modulePath = new URL("../apps/web/lib/tutor-stream-lifecycle-trace.ts", import.meta.url);

function loadTraceModule() {
  const source = readFileSync(modulePath, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = { exports: {} };
  new Function("exports", "module", "require", output)(loaded.exports, loaded, require);
  return loaded.exports;
}

class MemoryStorage {
  values = new Map();

  getItem(key) {
    return this.values.get(key) ?? null;
  }

  setItem(key, value) {
    this.values.set(key, value);
  }
}

class FailingStorage {
  getItem() {
    throw new Error("storage disabled");
  }

  setItem() {
    throw new Error("storage disabled");
  }
}

test("bounds private lifecycle entries without retaining Student or Tutor content", () => {
  const { createTutorStreamLifecycleTrace } = loadTraceModule();
  const storage = new MemoryStorage();
  const trace = createTutorStreamLifecycleTrace({
    storage,
    maxEvents: 3,
    createTraceId: () => "trace-private",
    now: () => 1000,
  });
  const attempt = trace.start({ origin: "typed" });

  attempt.record("submit_attempt", { messageContent: "Student secret" });
  attempt.record("submit_accepted");
  attempt.record("fetch_started", { tutorText: "Tutor secret" });
  attempt.record("response_headers_received", { httpStatus: 200 });

  const entries = trace.read();
  assert.deepEqual(entries.map((entry) => entry.event), [
    "submit_accepted",
    "fetch_started",
    "response_headers_received",
  ]);
  assert.equal(entries[2].httpStatus, 200);
  assert.equal(JSON.stringify(entries).includes("Student secret"), false);
  assert.equal(JSON.stringify(entries).includes("Tutor secret"), false);
  assert.equal(JSON.stringify(storage.values.get("lina:tutor-stream-lifecycle:v1")).includes("Student secret"), false);
});

test("records a suggested action delayed EOF separately from the later ready state", () => {
  const { createTutorStreamLifecycleTrace } = loadTraceModule();
  const timestamps = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 309];
  const trace = createTutorStreamLifecycleTrace({
    storage: new MemoryStorage(),
    createTraceId: () => "trace-delayed-eof",
    now: () => timestamps.shift(),
  });
  const attempt = trace.start({ origin: "suggested_action", suggestedActionKind: "ANSWER_CHOICE" });

  attempt.record("suggested_action_click");
  attempt.record("submit_attempt");
  attempt.record("submit_accepted");
  attempt.record("fetch_started");
  attempt.record("response_headers_received", { httpStatus: 200 });
  attempt.record("stream_reader_started");
  attempt.record("first_delta_received");
  attempt.record("terminal_turn_received");
  attempt.record("ui_ready");
  attempt.record("stream_eof");

  const entries = trace.read();
  assert.deepEqual(entries.map((entry) => entry.event), [
    "suggested_action_click",
    "submit_attempt",
    "submit_accepted",
    "fetch_started",
    "response_headers_received",
    "stream_reader_started",
    "first_delta_received",
    "terminal_turn_received",
    "ui_ready",
    "stream_eof",
  ]);
  assert.equal(entries.every((entry) => entry.traceId === "trace-delayed-eof"), true);
  assert.equal(entries[0].origin, "suggested_action");
  assert.equal(entries[0].suggestedActionKind, "ANSWER_CHOICE");
  assert.equal(entries[8].elapsedMs - entries[7].elapsedMs, 1);
  assert.equal(entries[9].elapsedMs - entries[8].elapsedMs, 300);
});

test("storage failure cannot prevent an in-memory lifecycle trace", () => {
  const { createTutorStreamLifecycleTrace } = loadTraceModule();
  const trace = createTutorStreamLifecycleTrace({
    storage: new FailingStorage(),
    createTraceId: () => "trace-storage-failure",
    now: () => 1000,
  });

  const attempt = trace.start({ origin: "typed" });
  assert.doesNotThrow(() => attempt.record("submit_attempt"));
  assert.deepEqual(trace.read().map((entry) => entry.event), ["submit_attempt"]);
});
