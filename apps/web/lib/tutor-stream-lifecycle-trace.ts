export const TUTOR_STREAM_LIFECYCLE_STORAGE_KEY = "lina:tutor-stream-lifecycle:v1";
export const TUTOR_STREAM_LIFECYCLE_MAX_EVENTS = 75;

export type TutorStreamLifecycleEvent =
  | "submit_attempt"
  | "submit_accepted"
  | "suggested_action_click"
  | "fetch_started"
  | "response_headers_received"
  | "stream_reader_started"
  | "first_delta_received"
  | "terminal_turn_received"
  | "stream_eof"
  | "ui_ready"
  | "request_error";

export type TutorStreamLifecycleOrigin = "typed" | "suggested_action";

export type TutorStreamLifecycleEntry = {
  traceId: string;
  event: TutorStreamLifecycleEvent;
  timestamp: string;
  elapsedMs: number;
  origin: TutorStreamLifecycleOrigin;
  suggestedActionKind?: "NAVIGATION" | "ANSWER_CHOICE";
  httpStatus?: number;
};

type BrowserStorage = Pick<Storage, "getItem" | "setItem">;

type TraceOptions = {
  storage?: BrowserStorage | null;
  maxEvents?: number;
  now?: () => number;
  createTraceId?: () => string;
};

type TraceStart = {
  origin: TutorStreamLifecycleOrigin;
  suggestedActionKind?: "NAVIGATION" | "ANSWER_CHOICE";
};

type TraceMetadata = {
  httpStatus?: number;
};

const lifecycleEvents = new Set<TutorStreamLifecycleEvent>([
  "submit_attempt",
  "submit_accepted",
  "suggested_action_click",
  "fetch_started",
  "response_headers_received",
  "stream_reader_started",
  "first_delta_received",
  "terminal_turn_received",
  "stream_eof",
  "ui_ready",
  "request_error",
]);

function browserSessionStorage(): BrowserStorage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function opaqueTraceId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `trace-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function validHttpStatus(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 100 && value <= 599;
}

function entryFrom(value: unknown): TutorStreamLifecycleEntry | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Record<string, unknown>;
  if (
    typeof candidate.traceId !== "string"
    || !lifecycleEvents.has(candidate.event as TutorStreamLifecycleEvent)
    || typeof candidate.timestamp !== "string"
    || typeof candidate.elapsedMs !== "number"
    || (candidate.origin !== "typed" && candidate.origin !== "suggested_action")
  ) {
    return null;
  }
  const entry: TutorStreamLifecycleEntry = {
    traceId: candidate.traceId,
    event: candidate.event as TutorStreamLifecycleEvent,
    timestamp: candidate.timestamp,
    elapsedMs: candidate.elapsedMs,
    origin: candidate.origin,
  };
  if (candidate.suggestedActionKind === "NAVIGATION" || candidate.suggestedActionKind === "ANSWER_CHOICE") {
    entry.suggestedActionKind = candidate.suggestedActionKind;
  }
  if (validHttpStatus(candidate.httpStatus)) entry.httpStatus = candidate.httpStatus;
  return entry;
}

function storedEntries(storage: BrowserStorage | null): TutorStreamLifecycleEntry[] {
  if (!storage) return [];
  try {
    const parsed: unknown = JSON.parse(storage.getItem(TUTOR_STREAM_LIFECYCLE_STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed)
      ? parsed.map(entryFrom).filter((entry): entry is TutorStreamLifecycleEntry => entry !== null)
      : [];
  } catch {
    return [];
  }
}

export function createTutorStreamLifecycleTrace({
  storage = browserSessionStorage(),
  maxEvents = TUTOR_STREAM_LIFECYCLE_MAX_EVENTS,
  now = () => Date.now(),
  createTraceId = opaqueTraceId,
}: TraceOptions = {}) {
  const retainedEvents = Number.isFinite(maxEvents)
    ? Math.max(1, Math.floor(maxEvents))
    : TUTOR_STREAM_LIFECYCLE_MAX_EVENTS;
  let entries = storedEntries(storage).slice(-retainedEvents);

  const persist = () => {
    if (!storage) return;
    try {
      storage.setItem(TUTOR_STREAM_LIFECYCLE_STORAGE_KEY, JSON.stringify(entries));
    } catch {
      // Lifecycle diagnostics are best-effort and must never block tutoring.
    }
  };

  return {
    start({ origin, suggestedActionKind }: TraceStart) {
      const traceId = createTraceId();
      const startedAt = now();
      return {
        traceId,
        record(event: TutorStreamLifecycleEvent, metadata: TraceMetadata = {}) {
          const observedAt = now();
          const entry: TutorStreamLifecycleEntry = {
            traceId,
            event,
            timestamp: new Date(observedAt).toISOString(),
            elapsedMs: Math.max(0, observedAt - startedAt),
            origin,
          };
          if (suggestedActionKind) entry.suggestedActionKind = suggestedActionKind;
          if (validHttpStatus(metadata.httpStatus)) entry.httpStatus = metadata.httpStatus;
          entries = [...entries, entry].slice(-retainedEvents);
          persist();
        },
      };
    },
    read(): TutorStreamLifecycleEntry[] {
      return entries.map((entry) => ({ ...entry }));
    },
  };
}
