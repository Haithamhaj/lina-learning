import assert from "node:assert/strict";
import test from "node:test";

import { dailyPresentationCopy } from "./daily-presentation-copy.ts";

test("Arabic Daily chrome uses Arabic student, voice, and source labels", () => {
  const copy = dailyPresentationCopy("rtl");

  assert.equal(copy.student, "أنتِ");
  assert.equal(copy.linaThinking, "لينا تفكّر…");
  assert.equal(copy.voice.record, "سجّلي رسالة صوتية");
  assert.equal(copy.source.add, "أضيفي صورة أو ملفًا");
});

test("English Daily chrome retains English learner-facing labels", () => {
  const copy = dailyPresentationCopy("ltr");

  assert.equal(copy.student, "You");
  assert.equal(copy.voice.record, "Record a message");
  assert.equal(copy.source.add, "Add photo or file");
});
