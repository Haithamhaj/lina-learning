import assert from "node:assert/strict";
import test from "node:test";
import { dailySessionRequest, dailySessionUrl } from "./daily-session-reference";

test("an initial Daily visit creates, while reload retains the exact server resource ID", () => {
  const initial = "https://example.test/student/daily";
  assert.deepEqual(dailySessionRequest(initial), {});
  const retained = dailySessionUrl(initial, "a923c361-b2b4-4100-922f-0fae930d721a");
  assert.equal(retained, "/student/daily?session=a923c361-b2b4-4100-922f-0fae930d721a");
  assert.deepEqual(dailySessionRequest(new URL(retained, initial).href), { learning_session_id: "a923c361-b2b4-4100-922f-0fae930d721a" });
});

test("invalid supplied references remain supplied for server rejection, never implicit creation", () => {
  assert.deepEqual(dailySessionRequest("https://example.test/student/daily?session="), { learning_session_id: "" });
  assert.deepEqual(dailySessionRequest("https://example.test/student/daily?session=invalid"), { learning_session_id: "invalid" });
});

test("only an explicit new-session action removes the previous reference", () => {
  assert.equal(dailySessionUrl("https://example.test/student/daily?session=old", null), "/student/daily");
});
