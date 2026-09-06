export type DailyChatAttempt = {
  studentMessageId: string | null;
  provisionalTutorMessageId: string;
  admitted: boolean;
  terminalTurnReceived: boolean;
};

/** Read the identity only after CORS has admitted this response to browser code. */
export function admittedDailyStudentMessageId(response: Pick<Response, "headers">): string | null {
  return response.headers.get("X-Lina-Student-Message-ID");
}

/** Replace a local attempt identity with the server's admitted Student identity. */
export function replaceDailyStudentMessageId<T extends { id: string }>(
  messages: readonly T[],
  temporaryStudentMessageId: string,
  durableStudentMessageId: string | null,
): T[] {
  if (durableStudentMessageId === null) return [...messages];
  return messages.map((message) => (
    message.id === temporaryStudentMessageId ? { ...message, id: durableStudentMessageId } : message
  ));
}

/** Remove only presentation rows that the server has not made durable. */
export function settleDailyChatAttempt<T extends { id: string }>(
  messages: readonly T[],
  attempt: DailyChatAttempt,
): T[] {
  if (attempt.terminalTurnReceived) return [...messages];
  const idsToRemove = new Set([attempt.provisionalTutorMessageId]);
  if (!attempt.admitted && attempt.studentMessageId !== null) idsToRemove.add(attempt.studentMessageId);
  return messages.filter((message) => !idsToRemove.has(message.id));
}
