import assert from "node:assert/strict";
import test from "node:test";

import { nextWorkspacePresentation } from "./daily-workspace-presentation.ts";

test("a newly active scene opens the Workspace", () => {
  assert.deepEqual(nextWorkspacePresentation("scene-a", null), { hiddenSceneId: null, visible: true });
});

test("hiding a scene keeps later versions of that same scene hidden", () => {
  assert.deepEqual(nextWorkspacePresentation("scene-a", "scene-a"), { hiddenSceneId: "scene-a", visible: false });
});

test("reopening clears only the local hide choice", () => {
  assert.deepEqual(nextWorkspacePresentation("scene-a", null), { hiddenSceneId: null, visible: true });
});

test("a different active scene opens the Workspace", () => {
  assert.deepEqual(nextWorkspacePresentation("scene-b", "scene-a"), { hiddenSceneId: null, visible: true });
});

test("removing the active scene clears stale hidden presentation state", () => {
  assert.deepEqual(nextWorkspacePresentation(null, "scene-a"), { hiddenSceneId: null, visible: false });
});
