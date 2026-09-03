import { StudioFrame, StudioOperation, StudioProtocolParseError } from "./contracts";
import { StudioSseParser } from "./sse";

type RuntimeOpen = {
  runtime_id: string;
  learning_session_id: string;
  status: string;
  latest_event_sequence: number;
};

type ControllerOptions = {
  apiBaseUrl: string;
  getToken: () => Promise<string | null>;
  fetch?: typeof globalThis.fetch;
  onFrame?: (frame: StudioFrame) => void;
  onError?: (message: string) => void;
};

export type StudioController = {
  open: (learningSessionId: string) => Promise<RuntimeOpen>;
  snapshot: (runtimeId: string) => Promise<unknown>;
  submit: (runtimeId: string, operation: StudioOperation) => Promise<unknown>;
  connect: (runtimeId: string) => { close: () => void; done: Promise<void> };
  latestSequence: () => number;
};

function endpoint(base: string, path: string): string {
  return `${base.replace(/\/$/, "")}${path}`;
}

function protocolError(response: Response): Error {
  return new Error(`Studio request failed (${response.status}).`);
}

/**
 * Project-owned protocol controller. It stores no Studio truth: a Snapshot and
 * sequenced feed replay remain the server-side reconstruction boundary.
 */
export function createStudioController(options: ControllerOptions): StudioController {
  const fetchImpl = options.fetch ?? globalThis.fetch;
  let sequence = 0;

  const authorized = async (): Promise<Headers> => {
    const token = await options.getToken();
    if (!token) throw new Error("Studio authentication is unavailable.");
    return new Headers({ Authorization: `Bearer ${token}` });
  };

  const request = async (path: string, init: RequestInit = {}): Promise<Response> => {
    const headers = await authorized();
    new Headers(init.headers).forEach((value, key) => headers.set(key, value));
    const response = await fetchImpl(endpoint(options.apiBaseUrl, path), { ...init, headers });
    if (!response.ok) throw protocolError(response);
    return response;
  };

  return {
    async open(learningSessionId) {
      const response = await request(`/api/v1/student/studio/session/${encodeURIComponent(learningSessionId)}/open`, {
        method: "POST",
      });
      const payload = await response.json() as RuntimeOpen;
      if (typeof payload.runtime_id !== "string" || typeof payload.latest_event_sequence !== "number") {
        throw new StudioProtocolParseError("Invalid Studio open response.");
      }
      sequence = payload.latest_event_sequence;
      return payload;
    },

    async snapshot(runtimeId) {
      const response = await request(`/api/v1/student/studio/${encodeURIComponent(runtimeId)}/snapshot`);
      return response.json();
    },

    async submit(runtimeId, operation) {
      const response = await request(`/api/v1/student/studio/${encodeURIComponent(runtimeId)}/operations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(operation),
      });
      return response.json();
    },

    connect(runtimeId) {
      const abort = new AbortController();
      const done = (async () => {
        const response = await request(
          `/api/v1/student/studio/${encodeURIComponent(runtimeId)}/events/stream?after_sequence=${sequence}`,
          { signal: abort.signal },
        );
        if (!response.body) throw new StudioProtocolParseError("Studio stream has no body.");
        const parser = new StudioSseParser();
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        try {
          while (!abort.signal.aborted) {
            const next = await reader.read();
            if (next.done) break;
            for (const parsed of parser.push(decoder.decode(next.value, { stream: true }))) {
              if (parsed.frame.type === "STUDIO_SNAPSHOT") sequence = parsed.frame.latest_event_sequence;
              if (parsed.frame.type === "STUDIO_EVENT_COMMITTED") sequence = parsed.frame.sequence;
              options.onFrame?.(parsed.frame);
            }
          }
        } finally {
          reader.releaseLock();
        }
      })().catch((error: unknown) => {
        if (!abort.signal.aborted) options.onError?.(error instanceof Error ? error.message : "Studio stream failed.");
      });
      return { close: () => abort.abort(), done };
    },

    latestSequence: () => sequence,
  };
}
