import type { CompositionView } from "./composition-recovery.ts";

export type CanvasLifecycleNoticeKind = "preparing" | "ready" | "failed" | "rejected" | "cancelled";

export type CanvasLifecycleNotice = {
  id: string;
  runId: string;
  kind: CanvasLifecycleNoticeKind;
  observedAt: string;
  direction?: "ltr" | "rtl";
};

const letterPattern = new RegExp("\\p{L}", "gu");
const arabicPattern = new RegExp("\\p{Script=Arabic}", "u");
const latinPattern = new RegExp("\\p{Script=Latin}", "u");

/** Use only Chat text; neutral notation leaves the current language unchanged. */
export function conversationNoticeDirection(
  messages: ReadonlyArray<{ role: "student" | "tutor"; content: string }>,
): "ltr" | "rtl" | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const letters = messages[index].content.match(letterPattern) ?? [];
    const arabic = letters.filter((letter) => arabicPattern.test(letter)).length;
    const latin = letters.filter((letter) => latinPattern.test(letter)).length;
    if (arabic > latin) return "rtl";
    if (latin > arabic) return "ltr";
  }
  return null;
}

/** These are local presentation events, never LearningSession messages or Tutor turns. */
export function canvasLifecycleNotice(view: CompositionView): CanvasLifecycleNotice | null {
  if (!view.run_id) return null;
  let kind: CanvasLifecycleNoticeKind;
  let milestone: string;
  switch (view.run_status) {
    case "PENDING":
    case "RUNNING":
      kind = "preparing";
      milestone = "start";
      break;
    case "COMPLETED":
      // The authoritative status projection has accepted the Scene. This does
      // not claim that the browser has already painted it.
      if (!view.scene_ready) return null;
      kind = "ready";
      milestone = "ready";
      break;
    case "FAILED":
    case "REJECTED":
    case "CANCELLED":
      kind = view.run_status.toLowerCase() as CanvasLifecycleNoticeKind;
      milestone = "terminal";
      break;
    default:
      return null;
  }
  return { id: `${view.run_id}:${milestone}`, runId: view.run_id, kind, observedAt: view.observed_at };
}

export function claimCanvasLifecycleNotice(view: CompositionView, seen: Set<string>): CanvasLifecycleNotice | null {
  const notice = canvasLifecycleNotice(view);
  if (!notice || seen.has(notice.id)) return null;
  seen.add(notice.id);
  return notice;
}

/** Only run IDs and notice milestones are stored, scoped to this browser tab and session. */
export function readSeenCanvasNotices(storage: Pick<Storage, "getItem"> | null, sessionId: string): Set<string> {
  try {
    const parsed: unknown = JSON.parse(storage?.getItem(canvasNoticeStorageKey(sessionId)) ?? "[]");
    return new Set(Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : []);
  } catch {
    return new Set();
  }
}

export function saveSeenCanvasNotices(storage: Pick<Storage, "setItem"> | null, sessionId: string, seen: Set<string>): void {
  try {
    storage?.setItem(canvasNoticeStorageKey(sessionId), JSON.stringify(Array.from(seen)));
  } catch {
    // Private browsing or storage limits must not block Chat or Canvas.
  }
}

function canvasNoticeStorageKey(sessionId: string): string {
  return `lina-canvas-lifecycle-v1:${sessionId}`;
}
