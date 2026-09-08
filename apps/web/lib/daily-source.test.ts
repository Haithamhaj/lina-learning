import assert from "node:assert/strict";
import test from "node:test";

import {
  buildDailySourceSubmission,
  latestActiveStudentSource,
  validateDailySourceFile,
} from "./daily-source.ts";

test("source-only submission uses the bounded default prompt and preserves the File", () => {
  const file = new File(["image"], "work.png", { type: "image/png" });
  const submission = buildDailySourceSubmission({ content: "", file, activeSourceId: null });

  assert.equal(submission.studentContent, "Help me with this.");
  assert.equal(submission.form.get("content"), "");
  assert.equal(submission.form.get("source"), file);
  assert.equal(submission.form.has("source_asset_id"), false);
});

test("a follow-up carries the Lina asset id without duplicating the original", () => {
  const submission = buildDailySourceSubmission({
    content: "Which number should I use?",
    file: null,
    activeSourceId: "asset-1",
  });

  assert.equal(submission.studentContent, "Which number should I use?");
  assert.equal(submission.form.get("source_asset_id"), "asset-1");
  assert.equal(submission.form.has("source"), false);
});

test("latest Student source establishes continuity, while a later text-only message does not invent one", () => {
  const source = { id: "asset-1", kind: "IMAGE" as const, filename: "work.png", content_type: "image/png", size_bytes: 5, preview_url: "/preview" };
  const replacement = { ...source, id: "asset-2", filename: "new.png" };
  assert.equal(latestActiveStudentSource([
    { role: "student", source_asset: source },
    { role: "tutor", source_asset: null },
    { role: "student", source_asset: replacement },
  ])?.id, "asset-2");
  assert.equal(latestActiveStudentSource([{ role: "student", source_asset: null }]), null);
});

test("browser preflight mirrors image, PDF, DOCX and application size bounds", () => {
  assert.equal(validateDailySourceFile(new File(["x"], "work.webp", { type: "image/webp" })), null);
  assert.match(validateDailySourceFile(new File(["x"], "work.txt", { type: "text/plain" })) ?? "", /PNG, JPEG, WEBP, PDF, or DOCX/);
  assert.match(validateDailySourceFile(new File([new Uint8Array(10 * 1024 * 1024 + 1)], "work.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" })) ?? "", /10 MiB/);
});
