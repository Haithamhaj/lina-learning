import assert from "node:assert/strict";
import test from "node:test";

import {
  admittedDailyStudentMessageId,
  replaceDailyStudentMessageId,
  settleDailyChatAttempt,
} from "./daily-chat-admission";

type Message = { id: string; role: "student" | "tutor"; content: string };

const history: Message[] = [{ id: "persisted-tutor", role: "tutor", content: "What would you like to try?" }];
const attempted: Message[] = [
  ...history,
  { id: "temporary-student", role: "student", content: "My typed answer" },
  { id: "temporary-tutor", role: "tutor", content: "" },
];

test("a Daily HTTP rejection before admission removes both temporary chat rows", () => {
  assert.deepEqual(
    settleDailyChatAttempt(attempted, {
      studentMessageId: "temporary-student",
      provisionalTutorMessageId: "temporary-tutor",
      admitted: false,
      terminalTurnReceived: false,
    }),
    history,
  );
});

test("a Daily stream failure after admission retains the admitted Student row but removes provisional Tutor", () => {
  assert.deepEqual(
    settleDailyChatAttempt(attempted, {
      studentMessageId: "temporary-student",
      provisionalTutorMessageId: "temporary-tutor",
      admitted: true,
      terminalTurnReceived: false,
    }),
    [...history, { id: "temporary-student", role: "student", content: "My typed answer" }],
  );
});

test("an admitted cross-origin response replaces the temporary Student ID before a later stream failure", () => {
  const response = new Response(null, {
    headers: { "X-Lina-Student-Message-ID": "durable-student" },
  });
  const durableStudentMessageId = admittedDailyStudentMessageId(response);

  assert.equal(durableStudentMessageId, "durable-student");
  const identified = replaceDailyStudentMessageId(attempted, "temporary-student", durableStudentMessageId);
  assert.deepEqual(
    settleDailyChatAttempt(identified, {
      studentMessageId: durableStudentMessageId,
      provisionalTutorMessageId: "temporary-tutor",
      admitted: true,
      terminalTurnReceived: false,
    }),
    [...history, { id: "durable-student", role: "student", content: "My typed answer" }],
  );
});

test("a terminal Tutor turn retains the single admitted Student row and its terminal Tutor row", () => {
  assert.deepEqual(
    settleDailyChatAttempt(attempted, {
      studentMessageId: "temporary-student",
      provisionalTutorMessageId: "temporary-tutor",
      admitted: true,
      terminalTurnReceived: true,
    }),
    attempted,
  );
});
