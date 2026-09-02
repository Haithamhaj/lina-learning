"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useRef, useState } from "react";

import { publicConfig } from "@/lib/public-config";
import { createTutorStreamLifecycleTrace } from "@/lib/tutor-stream-lifecycle-trace";
import {
  finalizeTutorStream,
  type TutorStreamTermination,
} from "@/lib/tutor-stream-turn-protocol";

export type DailySuggestedAction = {
  label: string;
  kind: "NAVIGATION" | "ANSWER_CHOICE";
};

export type DailyGuidedLearningCheck = {
  id: string;
  prompt: string;
  choices: Array<{ label: string }>;
};

export type DailyLearningMessage = {
  id: string;
  role: "student" | "tutor";
  content: string;
  created_at: string;
  suggested_actions: DailySuggestedAction[];
  guided_check?: DailyGuidedLearningCheck | null;
};

type DailyMathSession = {
  id: string;
  messages: DailyLearningMessage[];
};

type DailyTutorTurn = {
  text: string;
  suggested_actions?: DailySuggestedAction[];
  guided_check?: DailyGuidedLearningCheck | null;
};

export type DailySendOptions = {
  suggestedAction?: boolean;
  suggestedActionKind?: DailySuggestedAction["kind"];
  guidedCheckId?: string;
};

export type DailyTutorState = "loading" | "ready" | "streaming" | "error";

function localMessageId(participant: "student" | "tutor") {
  return `daily-${participant}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function errorFrom(response: Response): Promise<Error> {
  const payload = (await response.json().catch(() => ({}))) as { detail?: string };
  return new Error(payload.detail ?? "Tutor could not respond right now.");
}

function parseEvent(frame: string): { type: string; payload: unknown } | null {
  const type = frame.match(/^event: (.+)$/m)?.[1];
  const rawData = frame.match(/^data: (.+)$/m)?.[1];
  if (!type || !rawData) return null;
  try {
    return { type, payload: JSON.parse(rawData) as unknown };
  } catch {
    return null;
  }
}

export function useDailyTutorSession() {
  const { getToken, isLoaded } = useAuth();
  const [session, setSession] = useState<DailyMathSession | null>(null);
  const [state, setState] = useState<DailyTutorState>("loading");
  const [error, setError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const lifecycleTrace = useRef(createTutorStreamLifecycleTrace()).current;

  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;

    const load = async () => {
      setState("loading");
      try {
        const token = await getToken();
        const response = await fetch(`${publicConfig.apiBaseUrl}/v1/student/math/session`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw await errorFrom(response);
        const next = (await response.json()) as DailyMathSession;
        if (!cancelled) {
          setSession(next);
          setError("");
          setState("ready");
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Your learning room could not be opened.");
          setState("error");
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, loadAttempt]);

  const sendMessage = useCallback(async (nextContent: string, options: DailySendOptions = {}) => {
    const content = nextContent.trim();
    if (!session || !content || state === "streaming") return;

    const trace = lifecycleTrace.start({
      origin: options.suggestedAction ? "suggested_action" : "typed",
      suggestedActionKind: options.suggestedActionKind,
    });
    if (options.suggestedAction) trace.record("suggested_action_click");
    trace.record("submit_attempt");
    trace.record("submit_accepted");
    setError("");
    setState("streaming");

    const now = new Date().toISOString();
    const studentId = localMessageId("student");
    const tutorId = localMessageId("tutor");
    let terminalTurnReceived = false;
    let requestErrorRecorded = false;

    const removeProvisionalTutor = (termination: TutorStreamTermination) => {
      const outcome = finalizeTutorStream({
        messages: [],
        provisionalTutorMessageId: tutorId,
        terminalTurnReceived,
        termination,
      });
      if (outcome.lifecycleEvent === "stream_incomplete") {
        trace.record("stream_incomplete");
      } else if (!requestErrorRecorded) {
        trace.record("request_error");
      }
      setSession((current) => current ? {
        ...current,
        messages: finalizeTutorStream({
          messages: current.messages,
          provisionalTutorMessageId: tutorId,
          terminalTurnReceived,
          termination,
        }).messages,
      } : current);
      setError(outcome.error ?? "The Tutor response did not finish. Please try again.");
      setState(outcome.state);
    };

    setSession((current) => current ? {
      ...current,
      messages: [
        ...current.messages,
        { id: studentId, role: "student", content, created_at: now, suggested_actions: [] },
        { id: tutorId, role: "tutor", content: "", created_at: now, suggested_actions: [] },
      ],
    } : current);

    try {
      const token = await getToken();
      trace.record("fetch_started");
      const response = await fetch(`${publicConfig.apiBaseUrl}/v1/student/math/session/${session.id}/turn/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          content,
          suggested_action: Boolean(options.suggestedAction),
          guided_check_id: options.guidedCheckId,
        }),
      });
      trace.record("response_headers_received", { httpStatus: response.status });
      if (!response.ok) {
        trace.record("request_error", { httpStatus: response.status });
        requestErrorRecorded = true;
        throw await errorFrom(response);
      }
      if (!response.body) throw new Error("The Tutor response stream was unavailable.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let receivedDelta = false;
      trace.record("stream_reader_started");

      while (true) {
        const next = await reader.read();
        if (next.done) break;
        buffer += decoder.decode(next.value, { stream: true });
        const frames = buffer.replace(/\r\n/g, "\n").split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const event = parseEvent(frame);
          if (!event) continue;
          if (event.type === "delta" && typeof (event.payload as { text?: unknown }).text === "string") {
            if (!receivedDelta) {
              receivedDelta = true;
              trace.record("first_delta_received");
            }
            const delta = (event.payload as { text: string }).text;
            setSession((current) => current ? {
              ...current,
              messages: current.messages.map((message) => message.id === tutorId ? { ...message, content: `${message.content}${delta}` } : message),
            } : current);
          }
          if (event.type === "turn") {
            const turn = event.payload as DailyTutorTurn;
            if (typeof turn.text !== "string") continue;
            trace.record("terminal_turn_received");
            setSession((current) => current ? {
              ...current,
              messages: current.messages.map((message) => message.id === tutorId ? {
                ...message,
                content: turn.text,
                suggested_actions: Array.isArray(turn.suggested_actions) ? turn.suggested_actions : [],
                guided_check: turn.guided_check ?? null,
              } : message),
            } : current);
            terminalTurnReceived = true;
            setState("ready");
            trace.record("ui_ready");
          }
        }
      }

      trace.record("stream_eof");
      if (!terminalTurnReceived) removeProvisionalTutor("eof");
    } catch {
      if (!terminalTurnReceived) removeProvisionalTutor("error");
    }
  }, [getToken, lifecycleTrace, session, state]);

  return {
    messages: session?.messages ?? [],
    state,
    error,
    sendMessage,
    retryOpening: () => setLoadAttempt((attempt) => attempt + 1),
  };
}
