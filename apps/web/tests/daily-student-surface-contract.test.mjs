import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const root = new URL("../../../", import.meta.url);

function source(path) {
  return readFileSync(new URL(path, root), "utf8");
}

test("FE-02-UI-01 and FE-02-WORKSPACE-01 make the greenfield route a state-driven Learning Studio", () => {
  const page = source("apps/web/app/student/daily/page.tsx");
  const app = source("apps/web/components/daily-student/daily-student-app.tsx");
  const workspace = source("apps/web/components/daily-student/daily-learning-workspace.tsx");
  const routeSource = `${page}\n${app}\n${workspace}`;

  assert.match(page, /DailyStudentApp/);
  assert.doesNotMatch(routeSource, /student-math-session/i);
  assert.doesNotMatch(routeSource, /app\/student\/page/i);
  assert.match(app, /useDailyTutorSession/);
  assert.match(app, /DailyLearningWorkspace/);
  assert.match(app, /max-w-\[1540px\]/);
  assert.match(app, /lg:grid-cols-\[minmax\(23rem,0\.82fr\)_minmax\(0,1\.45fr\)\]/);
  assert.match(workspace, /Active learning workspace/);
  assert.match(workspace, /Studio canvas/);
  assert.match(workspace, /aria-label="Current learning focus"/);
  assert.match(workspace, /Visual reasoning map/);
  assert.match(workspace, /where we are now/i);
  assert.match(workspace, /messages/);
  assert.doesNotMatch(routeSource, /upload|attachment|microphone|video|iframe|three|canvas renderer/i);
});

test("FE-02-I18N-01 makes daily learner content and controls direction-aware", () => {
  const chat = source("apps/web/components/daily-student/daily-learning-chat.tsx");
  const workspace = source("apps/web/components/daily-student/daily-learning-workspace.tsx");

  assert.match(chat, /dir="auto"/);
  assert.match(chat, /htmlFor="daily-learning-message"/);
  assert.match(chat, /role="alert"/);
  assert.match(chat, /Tutor is thinking/);
  assert.match(workspace, /latestTutorMessage/);
  assert.match(workspace, /guidedCheck/);
  assert.doesNotMatch(chat, /paperclip|microphone|attachment|image upload/i);
});

test("FE-02-UI-01 keeps the premium composer reachable beside a bounded local transcript", () => {
  const chat = source("apps/web/components/daily-student/daily-learning-chat.tsx");

  assert.match(chat, /flex h-\[min\(72dvh,48rem\)\] min-h-\[36rem\] flex-col/);
  assert.match(chat, /lg:h-\[calc\(100dvh-10rem\)\]/);
  assert.match(chat, /overflow-y-auto/);
  assert.match(chat, /overscroll-contain/);
  assert.match(chat, /transcriptRef/);
  assert.match(chat, /followLiveEdge/);
  assert.match(chat, /scrollHeight/);
  assert.match(chat, /sticky bottom-0/);
  assert.match(chat, /Studio conversation/);
  assert.match(chat, /bg-\[linear-gradient/);
  assert.doesNotMatch(chat, /paperclip|microphone|attachment|image upload|workspace preview|video/i);
});

test("FE-02-WORKSPACE-01 derives a visually active board from real conversation state", () => {
  const workspace = source("apps/web/components/daily-student/daily-learning-workspace.tsx");

  assert.match(workspace, /latestStudentMessage/);
  assert.match(workspace, /latestTutorMessage/);
  assert.match(workspace, /ArithmeticSketch/);
  assert.match(workspace, /equationFrom/);
  assert.match(workspace, /\(\?!\\s\*\[\+−-\]\)/);
  assert.match(workspace, /state === "streaming"/);
  assert.match(workspace, /suggested_actions/);
  assert.match(workspace, /guided_check/);
  assert.match(workspace, /dir="auto"/);
  assert.match(workspace, /Tutor's shown step/);
  assert.match(workspace, /Tutor guidance/);
  assert.doesNotMatch(workspace, /fake|mock upload|placeholder attachment/i);
});
