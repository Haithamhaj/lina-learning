"use client";

import { useAuth } from "@clerk/nextjs";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { StudioRendererHost } from "@/components/daily-student/studio-renderer-host";
import { Button } from "@/components/ui/button";
import {
  createStudioController,
  type StudioController,
} from "@/lib/studio/controller";
import type { StudioOperation, StudioSnapshotFrame } from "@/lib/studio/contracts";
import { publicConfig } from "@/lib/public-config";
import { dailySessionRequest, dailySessionUrl } from "@/lib/daily-session-reference";
import {
  admittedDailyStudentMessageId,
  replaceDailyStudentMessageId,
  settleDailyChatAttempt,
} from "@/lib/daily-chat-admission";

type SuggestedAction = { label: string; kind: "NAVIGATION" | "ANSWER_CHOICE" };
type GuidedCheck = { id: string; prompt: string; choices: Array<{ label: string }> };
type ChatMessage = {
  id: string;
  role: "student" | "tutor";
  content: string;
  created_at: string;
  suggested_actions: SuggestedAction[];
  guided_check?: GuidedCheck | null;
};
type DailySession = { learning_session_id: string; status: string; messages: ChatMessage[] };
type TutorTurn = { text: string; suggested_actions: SuggestedAction[]; guided_check?: GuidedCheck | null };
type StudioConnection = { close: () => void; done: Promise<void> };

function studentEndpoint(path: string): string {
  return `${publicConfig.apiBaseUrl.replace(/\/$/, "")}/v1/student${path}`;
}

async function errorFrom(response: Response): Promise<Error> {
  const payload = await response.json().catch(() => ({})) as { detail?: string };
  return new Error(payload.detail ?? "This learning space is temporarily unavailable.");
}

function tutorMessage(id: string): ChatMessage {
  return { id, role: "tutor", content: "", created_at: new Date().toISOString(), suggested_actions: [] };
}

function ChatBubble({ message, pending }: { message: ChatMessage; pending: boolean }) {
  const tutor = message.role === "tutor";
  return (
    <article className={`flex gap-3 ${tutor ? "justify-start" : "justify-end"}`}>
      {tutor ? <span aria-hidden="true" className="mt-1 grid size-9 shrink-0 place-items-center rounded-2xl bg-[#17334f] text-sm text-white shadow-sm">✦</span> : null}
      <div className={`max-w-[85%] rounded-[1.35rem] px-4 py-3 text-sm leading-6 shadow-sm ${tutor ? "rounded-bl-md border border-[#cde7df] bg-[#effaf7] text-[#173d3a]" : "rounded-br-md bg-[#6658d3] text-white"}`}>
        <p className={`text-xs font-bold ${tutor ? "text-[#37796f]" : "text-[#ebe8ff]"}`}>{tutor ? "Tutor" : "You"}</p>
        {tutor && !message.content && pending ? <p className="mt-1.5">Tutor is thinking…</p> : <p dir="auto" className="mt-1.5 whitespace-pre-wrap">{message.content}</p>}
      </div>
      {!tutor ? <span aria-hidden="true" className="mt-1 grid size-9 shrink-0 place-items-center rounded-2xl bg-[#ece7ff] text-sm text-[#524596] shadow-sm">●</span> : null}
    </article>
  );
}

/**
 * The greenfield Daily surface owns only presentation and provisional state.
 * Tutor and Studio durability remain on their existing server authorities.
 */
export function DailyStudentApp() {
  const { getToken, isLoaded } = useAuth();
  const [learningSession, setLearningSession] = useState<DailySession | null>(null);
  const [snapshot, setSnapshot] = useState<StudioSnapshotFrame | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [chatSending, setChatSending] = useState(false);
  const [operationPending, setOperationPending] = useState(false);
  const [studioConnection, setStudioConnection] = useState<"connecting" | "connected" | "reconnecting" | "error">("connecting");
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [surfaceDirection, setSurfaceDirection] = useState<"ltr" | "rtl">("ltr");
  const controllerRef = useRef<StudioController | null>(null);
  const runtimeIdRef = useRef<string | null>(null);
  const appliedSnapshotSequenceRef = useRef(-1);
  const requiredSnapshotSequenceRef = useRef(0);
  const workspaceHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const composerRef = useRef<HTMLInputElement | null>(null);
  const priorWorkspaceVisible = useRef<boolean | null>(null);

  const applySnapshot = (next: StudioSnapshotFrame): boolean => {
    const required = Math.max(requiredSnapshotSequenceRef.current, appliedSnapshotSequenceRef.current);
    if (next.latest_event_sequence < required) return false;
    appliedSnapshotSequenceRef.current = next.latest_event_sequence;
    setSnapshot(next);
    return true;
  };

  useEffect(() => {
    setSurfaceDirection(navigator.language.toLowerCase().startsWith("ar") ? "rtl" : "ltr");
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    let reconnectTimer: number | undefined;
    let feed: StudioConnection | null = null;
    let retryCount = 0;

    const clearFeed = () => {
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      reconnectTimer = undefined;
      feed?.close();
      feed = null;
    };

    const load = async () => {
      setState("loading");
      setStudioConnection("connecting");
      setError("");
      setSessionEnded(false);
      setSnapshot(null);
      runtimeIdRef.current = null;
      appliedSnapshotSequenceRef.current = -1;
      requiredSnapshotSequenceRef.current = 0;
      clearFeed();
      try {
        const token = await getToken();
        if (cancelled) return;
        const response = await fetch(studentEndpoint("/daily/session"), {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          body: JSON.stringify(dailySessionRequest(window.location.href)),
        });
        if (cancelled) return;
        if (response.status === 409) {
          const lifecycle = await response.clone().json().catch(() => ({})) as { code?: string };
          if (lifecycle.code === "DAILY_SESSION_NOT_RESUMABLE") {
            setSessionEnded(true);
            setLearningSession(null);
          }
        }
        if (!response.ok) throw await errorFrom(response);
        const daily = await response.json() as DailySession;
        if (cancelled) return;
        window.history.replaceState(window.history.state, "", dailySessionUrl(window.location.href, daily.learning_session_id));
        setLearningSession(daily);

        const refreshSnapshot = async () => {
          const controller = controllerRef.current;
          const runtimeId = runtimeIdRef.current;
          if (!controller || !runtimeId) return;
          const next = await controller.snapshot(runtimeId);
          if (!cancelled) applySnapshot(next);
        };
        const connect = () => {
          if (cancelled || !runtimeIdRef.current || !controllerRef.current) return;
          setStudioConnection(retryCount === 0 ? "connected" : "reconnecting");
          feed = controllerRef.current.connect(runtimeIdRef.current);
          void feed.done.then(() => {
            if (cancelled) return;
            retryCount += 1;
            setStudioConnection("reconnecting");
            reconnectTimer = window.setTimeout(async () => {
              try {
                await refreshSnapshot();
                connect();
              } catch (reason) {
                if (!cancelled) {
                  setStudioConnection("error");
                  setError(reason instanceof Error ? reason.message : "The Workspace could not reconnect.");
                }
              }
            }, Math.min(4_000, 600 * retryCount));
          });
        };

        const controller = createStudioController({
          apiBaseUrl: publicConfig.apiBaseUrl,
          getToken,
          onFrame: (frame) => {
            if (cancelled) return;
            if (frame.type === "STUDIO_SNAPSHOT") {
              applySnapshot(frame);
              return;
            }
            if (frame.type === "STUDIO_EVENT_COMMITTED") {
              // Events advance the durable cursor; state is always refreshed
              // from the server Snapshot rather than reduced in the browser.
              requiredSnapshotSequenceRef.current = Math.max(requiredSnapshotSequenceRef.current, frame.sequence);
              void refreshSnapshot().catch((reason: unknown) => {
                if (!cancelled) setError(reason instanceof Error ? reason.message : "The Workspace could not refresh.");
              });
              return;
            }
            setStudioConnection("error");
          },
          onError: (message) => {
            if (!cancelled) setError(message);
          },
        });
        controllerRef.current = controller;
        const runtime = await controller.open(daily.learning_session_id);
        runtimeIdRef.current = runtime.runtime_id;
        await refreshSnapshot();
        if (cancelled) return;
        setState("ready");
        connect();
      } catch (reason) {
        if (!cancelled) {
          setState("error");
          setStudioConnection("error");
          setError(reason instanceof Error ? reason.message : "This learning space could not be opened.");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
      clearFeed();
      controllerRef.current = null;
      runtimeIdRef.current = null;
    };
  }, [getToken, isLoaded, loadAttempt]);

  const workspaceVisible = snapshot?.active_scene_contract !== null && snapshot !== null;
  useEffect(() => {
    const previous = priorWorkspaceVisible.current;
    priorWorkspaceVisible.current = workspaceVisible;
    if (previous === null || previous === workspaceVisible) return;
    const target = workspaceVisible ? workspaceHeadingRef.current : composerRef.current;
    window.requestAnimationFrame(() => target?.focus());
  }, [workspaceVisible]);

  const updateTutor = (id: string, update: (message: ChatMessage) => ChatMessage) => {
    setLearningSession((current) => current ? {
      ...current,
      messages: current.messages.map((message) => message.id === id ? update(message) : message),
    } : current);
  };

  const streamTutorTurn = async ({
    path,
    body,
    studentContent,
    restoreDraftOnPreAdmission = false,
  }: {
    path: string;
    body?: Record<string, unknown>;
    studentContent?: string;
    restoreDraftOnPreAdmission?: boolean;
  }): Promise<boolean> => {
    const provisionalTutorId = `daily-tutor-${crypto.randomUUID()}`;
    let studentMessageId = studentContent ? `daily-student-${crypto.randomUUID()}` : null;
    let terminalReceived = false;
    let admitted = false;
    setLearningSession((current) => current ? {
      ...current,
      messages: [
        ...current.messages,
        ...(studentContent ? [{
          id: studentMessageId!,
          role: "student" as const,
          content: studentContent,
          created_at: new Date().toISOString(),
          suggested_actions: [],
        }] : []),
        tutorMessage(provisionalTutorId),
      ],
    } : current);
    try {
      const token = await getToken();
      const response = await fetch(studentEndpoint(path), {
        method: "POST",
        headers: {
          ...(body ? { "Content-Type": "application/json" } : {}),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) throw await errorFrom(response);
      admitted = true;
      const durableStudentMessageId = admittedDailyStudentMessageId(response);
      if (studentMessageId && durableStudentMessageId) {
        const temporaryStudentMessageId = studentMessageId;
        studentMessageId = durableStudentMessageId;
        setLearningSession((current) => current ? {
          ...current,
          messages: replaceDailyStudentMessageId(
            current.messages,
            temporaryStudentMessageId,
            durableStudentMessageId,
          ),
        } : current);
      }
      if (!response.body) throw new Error("The Tutor response stream was unavailable.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const next = await reader.read();
        if (next.done) break;
        buffer += decoder.decode(next.value, { stream: true });
        const entries = buffer.split("\n\n");
        buffer = entries.pop() ?? "";
        for (const entry of entries) {
          const type = entry.match(/^event: (.+)$/m)?.[1];
          const raw = entry.match(/^data: (.+)$/m)?.[1];
          if (!type || !raw) continue;
          const payload = JSON.parse(raw) as { text?: string };
          if (type === "delta" && payload.text) {
            updateTutor(provisionalTutorId, (message) => ({ ...message, content: `${message.content}${payload.text}` }));
          }
          if (type === "turn") {
            const turn = payload as TutorTurn;
            terminalReceived = true;
            updateTutor(provisionalTutorId, (message) => ({
              ...message,
              content: turn.text,
              suggested_actions: turn.suggested_actions,
              guided_check: turn.guided_check ?? null,
            }));
          }
        }
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The Tutor response did not finish.");
    }
    if (!terminalReceived) {
      setLearningSession((current) => current ? {
        ...current,
        messages: settleDailyChatAttempt(current.messages, {
          studentMessageId,
          provisionalTutorMessageId: provisionalTutorId,
          admitted,
          terminalTurnReceived: terminalReceived,
        }),
      } : current);
      if (!admitted && studentContent && restoreDraftOnPreAdmission) setDraft(studentContent);
      setError("The Tutor response did not finish.");
    }
    return terminalReceived;
  };

  const sendChat = async (
    content: string,
    options: { suggestedAction?: boolean; guidedCheckId?: string } = {},
  ) => {
    const trimmed = content.trim();
    if (!learningSession || !trimmed || chatSending) return;
    setChatSending(true);
    setError("");
    setDraft("");
    await streamTutorTurn({
      path: `/daily/session/${learningSession.learning_session_id}/turn/stream`,
      body: {
        content: trimmed,
        suggested_action: options.suggestedAction ?? false,
        guided_check_id: options.guidedCheckId ?? null,
      },
      studentContent: trimmed,
      restoreDraftOnPreAdmission: !options.suggestedAction && !options.guidedCheckId,
    });
    setChatSending(false);
  };

  const reloadSnapshot = async () => {
    const controller = controllerRef.current;
    const runtimeId = runtimeIdRef.current;
    if (!controller || !runtimeId) return;
    try {
      applySnapshot(await controller.snapshot(runtimeId));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The Workspace could not reload.");
    }
  };

  const submitOperation = async (operation: StudioOperation) => {
    const controller = controllerRef.current;
    const runtimeId = runtimeIdRef.current;
    if (!controller || !runtimeId) throw new Error("The Workspace is not connected.");
    setOperationPending(true);
    setError("");
    try {
      const result = await controller.submit(runtimeId, operation);
      requiredSnapshotSequenceRef.current = Math.max(requiredSnapshotSequenceRef.current, result.sequence);
      applySnapshot(await controller.snapshot(runtimeId));
      if (!result.replayed && result.student_interaction_id && result.student_interaction_status === "PENDING") {
        await streamTutorTurn({
          path: `/studio/${runtimeId}/interactions/${result.student_interaction_id}/turn/stream`,
        });
      }
    } catch (reason) {
      // Re-read the durable Snapshot after a stale/rejected optimistic attempt.
      await reloadSnapshot();
      const message = reason instanceof Error ? reason.message : "Studio could not save that action.";
      setError(message);
      throw new Error(message);
    } finally {
      setOperationPending(false);
    }
  };

  const latestTutor = [...(learningSession?.messages ?? [])].reverse().find((message) => message.role === "tutor");
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendChat(draft);
  };

  if (state === "loading") {
    return <main className="grid min-h-screen place-items-center bg-[#f7f8fc] p-6 text-sm text-slate-600">Opening your Daily learning space…</main>;
  }
  if (state === "error" && !learningSession) {
    return <main className="grid min-h-screen place-items-center bg-[#f7f8fc] p-6"><section className="max-w-md rounded-[2rem] bg-white p-7 text-center shadow-sm" role="alert"><h1 className="font-display text-2xl text-slate-900">Let’s try again.</h1><p className="mt-3 text-sm leading-6 text-slate-600">{error}</p><Button className="mt-5" type="button" onClick={() => {
      if (sessionEnded) window.history.replaceState(window.history.state, "", dailySessionUrl(window.location.href, null));
      setLoadAttempt((value) => value + 1);
    }}>{sessionEnded ? "Start a new session" : "Reload Daily"}</Button></section></main>;
  }

  return (
    <main dir={surfaceDirection} className="min-h-screen bg-[radial-gradient(circle_at_top_left,#eef7f3_0%,transparent_36%),linear-gradient(135deg,#fbfaff_0%,#f7fbff_54%,#fff9f1_100%)] px-4 py-5 text-slate-900 sm:px-7 sm:py-8">
      <div className="mx-auto max-w-[1500px]">
        <header className="mb-5 flex flex-wrap items-end justify-between gap-4 rounded-[1.75rem] border border-white/90 bg-white/75 px-5 py-4 shadow-sm backdrop-blur sm:px-6">
          <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[#5d7d78]">Daily learning</p><h1 className="mt-1 font-display text-3xl tracking-tight">A calm place to think out loud.</h1></div>
          <p className="text-sm text-slate-600" role="status">Studio {studioConnection === "connected" ? "connected" : studioConnection === "reconnecting" ? "reconnecting" : studioConnection}</p>
        </header>
        <div className={`grid items-start gap-5 ${workspaceVisible ? "xl:grid-cols-[minmax(0,0.92fr)_minmax(420px,1.08fr)]" : ""}`}>
          <section aria-label="Learning Chat" className="rounded-[2rem] border border-white bg-white/95 p-4 shadow-[0_18px_50px_-34px_rgba(24,40,67,0.55)] sm:p-5">
            <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-4"><div><h2 className="font-display text-2xl">Learning Chat</h2><p className="mt-1 text-sm leading-6 text-slate-600">Ask, explain what you tried, or choose a next step with your Tutor.</p></div><span aria-hidden="true" className="grid size-10 place-items-center rounded-2xl bg-[#e8f6f1] text-[#2e766a]">✦</span></div>
            <div className="mt-4 min-h-[26rem] max-h-[calc(100vh-19rem)] overflow-y-auto rounded-[1.5rem] bg-[#fafbfe] p-3 sm:p-4" aria-live="polite">
              {learningSession?.messages.length ? <div className="grid gap-4">{learningSession.messages.map((message) => <div key={message.id}><ChatBubble message={message} pending={chatSending} />{message.role === "tutor" && message.id === latestTutor?.id && message.suggested_actions.length > 0 ? <div className="ml-12 mt-2 flex flex-wrap gap-2" aria-label="Tutor suggested actions">{message.suggested_actions.map((action) => <Button key={`${action.kind}:${action.label}`} className="h-auto min-h-10 rounded-full px-3 py-2 text-left" type="button" variant="secondary" disabled={chatSending} onClick={() => void sendChat(action.label, { suggestedAction: true })}><span dir="auto">{action.label}</span></Button>)}</div> : null}{message.role === "tutor" && message.id === latestTutor?.id && message.guided_check ? <div className="ml-12 mt-3 rounded-2xl border border-emerald-100 bg-white p-3"><p className="text-sm font-semibold" dir="auto">{message.guided_check.prompt}</p><div className="mt-2 flex flex-wrap gap-2">{message.guided_check.choices.map((choice) => <Button key={choice.label} type="button" variant="secondary" disabled={chatSending} onClick={() => void sendChat(choice.label, { guidedCheckId: message.guided_check?.id })}>{choice.label}</Button>)}</div></div> : null}</div>)}</div> : <div className="grid min-h-80 place-items-center px-5 text-center"><div className="max-w-sm"><div aria-hidden="true" className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#e9f7f3] text-2xl text-[#328577]">✎</div><h3 className="mt-4 font-display text-2xl">What are you working through?</h3><p className="mt-2 text-sm leading-6 text-slate-600">Start with a question, an answer you tried, or something you would like to understand more clearly.</p></div></div>}
            </div>
            <form className="mt-4 grid gap-3 rounded-[1.35rem] border border-slate-200 bg-white p-3 sm:grid-cols-[1fr_auto] sm:items-center" onSubmit={submit}>
              <label className="sr-only" htmlFor="daily-learning-message">Your message for Tutor</label>
              <input ref={composerRef} id="daily-learning-message" dir="auto" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={4000} placeholder="Ask a question or share what you tried" className="h-12 rounded-2xl bg-slate-50 px-4 text-sm outline-none ring-[#7d70df] transition focus:ring-2" />
              <Button className="min-h-12" type="submit" disabled={!draft.trim() || chatSending}>{chatSending ? "Tutor is thinking…" : "Send"}</Button>
            </form>
          </section>
          {workspaceVisible && snapshot ? <aside aria-label="Adaptive Learning Workspace" className="rounded-[2rem] border border-white bg-white/95 p-4 shadow-[0_18px_50px_-34px_rgba(24,40,67,0.55)] sm:p-5"><div className="mb-4 flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[#8a6b42]">Adaptive Learning Workspace</p><h2 ref={workspaceHeadingRef} tabIndex={-1} className="mt-1 font-display text-2xl outline-none">Work with the current scene</h2></div>{operationPending ? <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900" role="status">Saving…</span> : null}</div><StudioRendererHost snapshot={snapshot} operationPending={operationPending} onOperation={submitOperation} onReload={() => { void reloadSnapshot(); }} /></aside> : null}
        </div>
        {error ? <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-900" role="alert"><span>{error}</span><Button type="button" variant="secondary" onClick={() => setLoadAttempt((value) => value + 1)}>Reconnect</Button></div> : null}
      </div>
    </main>
  );
}
