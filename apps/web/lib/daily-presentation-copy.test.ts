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

test("Arabic Canvas waiting copy advances through truthful elapsed stages", () => {
  const canvas = dailyPresentationCopy("rtl").canvas;

  assert.equal(canvas.preparing(0), "أجهّز لك الرسم…");
  assert.equal(canvas.preparing(10), "أبني التمثيل البصري خطوة بخطوة…");
  assert.equal(canvas.preparing(30), "الرسم ما زال قيد التجهيز. يمكنكِ متابعة الشرح معي إلى أن يظهر.");
  assert.equal(canvas.elapsed(18), "جارٍ العمل منذ 18 ثانية");
  assert.equal(canvas.workspaceLabel, "مساحة Canvas التعليمية");
});

test("English Canvas waiting copy advances through equivalent elapsed stages", () => {
  const canvas = dailyPresentationCopy("ltr").canvas;

  assert.equal(canvas.preparing(0), "I’m preparing the visual for you…");
  assert.equal(canvas.preparing(10), "I’m building the visual step by step…");
  assert.equal(canvas.preparing(30), "The visual is still being prepared. You can keep learning with me while it appears.");
  assert.equal(canvas.elapsed(18), "Working for 18 seconds");
  assert.equal(canvas.statusUnavailable, "The visual status could not be refreshed just now.");
});
