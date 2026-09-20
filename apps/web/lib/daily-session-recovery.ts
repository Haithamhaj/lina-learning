import {
  latestActiveStudentSource,
  type StudentSourceAsset,
} from "./daily-source";

export type DailySessionLifecyclePayload = { code?: unknown; detail?: unknown };

/** Only the explicit lifecycle conflict may replace an initial URL reference. */
export function isNonResumableDailyOpenResponse(
  status: number,
  payload: DailySessionLifecyclePayload,
): boolean {
  return status === 409 && payload.code === "DAILY_SESSION_NOT_RESUMABLE";
}

/** An already-bound page may recover its stale turn-level 404 exactly once. */
export function isStaleDailyTurnResponse(
  status: number,
  payload: DailySessionLifecyclePayload,
): boolean {
  return status === 404 || isNonResumableDailyOpenResponse(status, payload);
}

/** Keep already rendered history while binding future activity to the replacement. */
export function mergeDailySessionMessages<T extends { id: string }>(
  preserved: readonly T[],
  replacement: readonly T[],
): T[] {
  const seen = new Set(preserved.map((message) => message.id));
  return [...preserved, ...replacement.filter((message) => !seen.has(message.id))];
}

export function shouldStartCanvasTutorStream(result: {
  student_interaction_id?: string | null;
  student_interaction_status?: string | null;
}): boolean {
  return Boolean(
    result.student_interaction_id
    && result.student_interaction_status === "PENDING"
  );
}

export function rebindRecoveredDailySession<
  TMessage extends { id: string; role: string; source_asset?: StudentSourceAsset | null },
  TSession extends { messages: TMessage[] },
  TSelected,
>({
  preservedMessages,
  replacement,
  selectedSource,
}: {
  preservedMessages: readonly TMessage[];
  replacement: TSession;
  selectedSource: TSelected;
}): {
  session: TSession;
  activeSource: StudentSourceAsset | null;
  selectedSource: TSelected;
} {
  return {
    session: {
      ...replacement,
      messages: mergeDailySessionMessages(preservedMessages, replacement.messages),
    },
    activeSource: latestActiveStudentSource(replacement.messages),
    selectedSource,
  };
}

/** Execute at most one replacement open, even if that response is also stale. */
export async function openDailySessionWithSingleReplacement<T>(
  initialRequest: Record<string, unknown>,
  open: (request: Record<string, unknown>) => Promise<T>,
  shouldReplace: (result: T) => Promise<boolean>,
): Promise<{ result: T; replaced: boolean }> {
  const initial = await open(initialRequest);
  if (!(await shouldReplace(initial))) return { result: initial, replaced: false };
  const replacedSessionId = initialRequest.learning_session_id;
  return {
    result: await open({ replacement_for_session_id: replacedSessionId }),
    replaced: true,
  };
}
