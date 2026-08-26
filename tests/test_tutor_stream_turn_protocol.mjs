import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const modulePath = new URL("../apps/web/lib/tutor-stream-turn-protocol.ts", import.meta.url);

function loadProtocolModule() {
  const source = readFileSync(modulePath, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const loaded = { exports: {} };
  new Function("exports", "module", "require", output)(loaded.exports, loaded, require);
  return loaded.exports;
}

const messages = [
  { id: "historical-tutor", role: "tutor", content: "Durable history" },
  { id: "current-student", role: "student", content: "Current question" },
  { id: "provisional-tutor", role: "tutor", content: "Complete-looking provisional answer" },
];

test("non-terminal stream errors discard only the provisional Tutor bubble", () => {
  const { finalizeTutorStream, INCOMPLETE_TUTOR_RESPONSE_ERROR } = loadProtocolModule();

  const result = finalizeTutorStream({
    messages,
    provisionalTutorMessageId: "provisional-tutor",
    terminalTurnReceived: false,
    termination: "error",
  });

  assert.deepEqual(result.messages.map((message) => message.id), ["historical-tutor", "current-student"]);
  assert.equal(result.state, "error");
  assert.equal(result.error, INCOMPLETE_TUTOR_RESPONSE_ERROR);
  assert.equal(result.lifecycleEvent, "request_error");
});

test("silent EOF without a terminal turn discards an empty thinking placeholder", () => {
  const { finalizeTutorStream, INCOMPLETE_TUTOR_RESPONSE_ERROR } = loadProtocolModule();

  const result = finalizeTutorStream({
    messages: [...messages.slice(0, 2), { id: "provisional-tutor", role: "tutor", content: "" }],
    provisionalTutorMessageId: "provisional-tutor",
    terminalTurnReceived: false,
    termination: "eof",
  });

  assert.deepEqual(result.messages.map((message) => message.id), ["historical-tutor", "current-student"]);
  assert.equal(result.state, "error");
  assert.equal(result.error, INCOMPLETE_TUTOR_RESPONSE_ERROR);
  assert.equal(result.lifecycleEvent, "stream_incomplete");
});

test("a terminal Tutor turn remains authoritative after EOF or a later reader error", () => {
  const { finalizeTutorStream } = loadProtocolModule();

  for (const termination of ["eof", "error"]) {
    const result = finalizeTutorStream({
      messages,
      provisionalTutorMessageId: "provisional-tutor",
      terminalTurnReceived: true,
      termination,
    });

    assert.equal(result.messages, messages);
    assert.equal(result.state, "ready");
    assert.equal(result.error, null);
    assert.equal(result.lifecycleEvent, null);
  }
});
