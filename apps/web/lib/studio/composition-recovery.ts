export type CompositionView = {
  observed_at: string;
  run_id: string | null;
  run_created_at: string | null;
  run_status: string;
  scene_ready: boolean;
};

const terminal = new Set(["IDLE", "COMPLETED", "FAILED", "REJECTED", "CANCELLED", "SUPERSEDED"]);
const failed = new Set(["FAILED", "REJECTED", "CANCELLED"]);

export type CanvasPresentationState = {
  showWorkspace: boolean;
  showWaiting: boolean;
  showUpdating: boolean;
  showFailure: boolean;
  animateWaiting: boolean;
};

export const canvasWaitingMotionClass = "motion-safe:animate-pulse motion-reduce:animate-none";

export function isCompositionInFlight(view: CompositionView | null): boolean {
  return view?.run_status === "PENDING" || view?.run_status === "RUNNING";
}

export function isCompositionTerminal(view: CompositionView | null): boolean {
  return view !== null && terminal.has(view.run_status);
}

export function canvasPresentationState(
  view: CompositionView | null,
  hasActiveScene: boolean,
): CanvasPresentationState {
  const inFlight = isCompositionInFlight(view);
  const showFailure = view !== null && failed.has(view.run_status);
  return {
    showWorkspace: hasActiveScene || inFlight || showFailure,
    showWaiting: inFlight && !hasActiveScene,
    showUpdating: inFlight && hasActiveScene,
    showFailure,
    animateWaiting: inFlight,
  };
}

export function canvasElapsedSeconds(runCreatedAt: string | null, now: number = Date.now()): number {
  if (runCreatedAt === null) return 0;
  const startedAt = Date.parse(runCreatedAt);
  if (Number.isNaN(startedAt)) return 0;
  return Math.max(0, Math.floor((now - startedAt) / 1_000));
}

export function shouldRefreshCompositionSnapshot(view: CompositionView): boolean {
  return view.run_status === "COMPLETED" && view.scene_ready;
}

export function isDailyComposerDisabled({
  tutorResponding,
  voiceBusy,
}: {
  tutorResponding: boolean;
  voiceBusy: boolean;
}): boolean {
  return tutorResponding || voiceBusy;
}

/** Preserve a newer known run when a stale poll returns an older identity. */
export function shouldReplaceCompositionView(current: CompositionView | null, next: CompositionView): boolean {
  if (current?.run_id && next.run_id && current.run_id !== next.run_id) {
    const currentCreatedAt = parseServerTime(current.run_created_at);
    const nextCreatedAt = parseServerTime(next.run_created_at);
    // A tie has no safe chronology. Keep the already-known run instead of
    // pretending UUIDs or delivery order express creation order.
    return currentCreatedAt !== null && nextCreatedAt !== null && nextCreatedAt > currentCreatedAt;
  }
  if (current?.run_id && next.run_id && current.run_id === next.run_id) {
    const currentObservedAt = parseServerTime(current.observed_at);
    const nextObservedAt = parseServerTime(next.observed_at);
    if (currentObservedAt === null || nextObservedAt === null || nextObservedAt < currentObservedAt) return false;
    if (nextObservedAt === currentObservedAt) {
      return !current.scene_ready && next.scene_ready;
    }
  }
  return true;
}

function parseServerTime(value: string | null): number | null {
  if (value === null) return null;
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}
