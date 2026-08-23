"use client";

import { useAuth } from "@clerk/nextjs";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { publicConfig } from "@/lib/public-config";

type Message = {
  id: string;
  role: string;
  content: string;
  created_at: string;
  suggested_actions: string[];
};

type MathSession = {
  id: string;
  subject: "MATH";
  status: "OPEN";
  messages: Message[];
};

type TutorTurn = {
  text: string;
  suggested_actions: string[];
};

function ChatAvatar({ participant }: { participant: "Lina" | "Tutor" }) {
  const isTutor = participant === "Tutor";
  return (
    <span
      aria-hidden="true"
      className={`flex size-10 shrink-0 items-center justify-center rounded-2xl text-sm font-bold shadow-sm ${isTutor ? "bg-[#17334f] text-[#f4fbff]" : "bg-[#eadbff] text-[#5b3d91]"}`}
    >
      {isTutor ? "✦" : "L"}
    </span>
  );
}

function MathMotifs() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <span className="absolute -left-8 top-16 grid size-28 place-items-center rounded-full border border-[#d9cbf4] bg-[#f1ebff]/70 text-3xl font-display text-[#8a6cbd]">½</span>
      <span className="absolute right-8 top-8 grid size-20 rotate-12 place-items-center rounded-[1.7rem] border border-[#bfe7df] bg-[#e5f7f2]/80 text-2xl font-display text-[#368879]">△</span>
      <span className="absolute bottom-24 right-[-1.5rem] grid size-24 -rotate-6 place-items-center rounded-full border border-[#f4d6ae] bg-[#fff3df]/80 text-2xl font-display text-[#cb7a34]">×</span>
      <span className="absolute bottom-8 left-1/4 text-4xl font-display text-[#d7c6f5]/70">+ 5</span>
    </div>
  );
}

async function errorFrom(response: Response): Promise<Error> {
  const payload = (await response.json().catch(() => ({}))) as { detail?: string };
  return new Error(payload.detail ?? "Your learning space could not be opened.");
}

export function StudentMathSession() {
  const { getToken, isLoaded } = useAuth();
  const [learningSession, setLearningSession] = useState<MathSession | null>(null);
  const [draft, setDraft] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "sending" | "error">("loading");
  const [error, setError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    const load = async () => {
      try {
        const token = await getToken();
        const response = await fetch(`${publicConfig.apiBaseUrl}/v1/student/math/session`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw await errorFrom(response);
        const next = (await response.json()) as MathSession;
        if (!cancelled) {
          setLearningSession(next);
          setError("");
          setState("ready");
        }
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "Your learning space could not be opened.");
          setState("error");
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, loadAttempt]);

  const sendMessage = async (nextContent: string, suggestedAction = false) => {
    const content = nextContent.trim();
    if (!learningSession || !content || state === "sending") return;
    setState("sending");
    setError("");
    try {
      const token = await getToken();
      const now = new Date().toISOString();
      const studentId = `local-student-${Date.now()}`;
      const tutorId = `local-tutor-${Date.now()}`;
      setLearningSession((current) => current ? {
        ...current,
        messages: [...current.messages, { id: studentId, role: "student", content, created_at: now, suggested_actions: [] }, { id: tutorId, role: "tutor", content: "", created_at: now, suggested_actions: [] }],
      } : current);
      setDraft("");
      const response = await fetch(`${publicConfig.apiBaseUrl}/v1/student/math/session/${learningSession.id}/turn/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content, suggested_action: suggestedAction }),
      });
      if (!response.ok) throw await errorFrom(response);
      if (!response.body) throw new Error("The Tutor response stream was unavailable.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const next = await reader.read();
        if (next.done) break;
        buffer += decoder.decode(next.value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const rawEvent of events) {
          const type = rawEvent.match(/^event: (.+)$/m)?.[1];
          const rawData = rawEvent.match(/^data: (.+)$/m)?.[1];
          if (!type || !rawData) continue;
          const payload = JSON.parse(rawData) as { text?: string };
          if (type === "delta" && payload.text) {
            setLearningSession((current) => current ? {
              ...current,
              messages: current.messages.map((message) => message.id === tutorId ? { ...message, content: `${message.content}${payload.text}` } : message),
            } : current);
          }
          if (type === "turn") {
            const turn = payload as TutorTurn;
            setLearningSession((current) => current ? {
              ...current,
              messages: current.messages.map((message) => message.id === tutorId ? { ...message, content: turn.text, suggested_actions: turn.suggested_actions } : message),
            } : current);
          }
        }
      }
      setState("ready");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Your message could not be saved.");
      setState("error");
    }
  };

  const send = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendMessage(draft);
  };

  if (state === "loading") {
    return <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">Opening your Math session…</p>;
  }
  if (state === "error" && !learningSession) {
    return (
      <section className="rounded-[2rem] border border-rose-100 bg-white p-6 text-center text-sm text-rose-800 shadow-sm" role="alert">
        <p className="font-semibold">Let’s try opening Math again.</p>
        <p className="mt-2 text-rose-700">{error}</p>
        <Button className="mt-5" type="button" onClick={() => setLoadAttempt((attempt) => attempt + 1)}>Try again</Button>
      </section>
    );
  }

  const latestActionableTutorMessageId = [...(learningSession?.messages ?? [])]
    .reverse()
    .find((message) => message.role === "tutor" && message.suggested_actions.length > 0)?.id;

  return (
    <section aria-label="Math learning session" className="relative overflow-hidden rounded-[2rem] border border-white/90 bg-white/95 p-4 shadow-[0_18px_60px_-34px_rgba(47,35,81,0.55)] sm:p-6">
      <MathMotifs />
      <div className="relative grid gap-5">
        <div className="flex items-start gap-4 rounded-[1.5rem] border border-[#ece6fa] bg-[#fbfaff] px-4 py-4 sm:px-5">
          <div aria-hidden="true" className="grid size-11 shrink-0 place-items-center rounded-2xl bg-[#e8ddff] text-xl text-[#60428e]">∠</div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#7557a7]">Your Math space</p>
            <h2 className="mt-1 font-display text-2xl text-ink">Pick up where you left off.</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">Ask, try an answer, or tell Tutor what feels tricky.</p>
          </div>
        </div>
        <div className="min-h-80 max-h-[28rem] overflow-y-auto rounded-[1.5rem] border border-[#ebe9f4] bg-[#f8f8fc]/90 p-3 sm:p-4" aria-live="polite">
          {learningSession?.messages.length ? <div className="grid gap-4">{learningSession.messages.map((message) => {
            const participant = message.role === "tutor" ? "Tutor" : "Lina";
            const isTutor = participant === "Tutor";
            const isThinking = isTutor && !message.content && state === "sending";
            return (
              <article className={`flex items-end gap-2.5 ${isTutor ? "justify-start" : "justify-end"}`} key={message.id}>
                {isTutor ? <ChatAvatar participant="Tutor" /> : null}
                <div className="max-w-[82%]">
                  <div className={`rounded-[1.35rem] px-4 py-3 shadow-sm ${isTutor ? "rounded-bl-md border border-[#d4e7e4] bg-[#edf9f7] text-[#163b3b]" : "rounded-br-md bg-[#6a4ba2] text-white"}`}>
                    <p className={`text-xs font-bold ${isTutor ? "text-[#418377]" : "text-[#eadfff]"}`}>{participant}</p>
                    {isThinking ? <p className="mt-1.5 flex items-center gap-2 text-sm"><span className="flex gap-1" aria-hidden="true"><span className="size-1.5 rounded-full bg-current opacity-60" /><span className="size-1.5 rounded-full bg-current opacity-80" /><span className="size-1.5 rounded-full bg-current" /></span>Tutor is thinking…</p> : <p dir="auto" className="mt-1.5 whitespace-pre-wrap text-sm leading-6">{message.content}</p>}
                  </div>
                  {isTutor && message.id === latestActionableTutorMessageId ? <div className="mt-2 flex flex-wrap gap-2" aria-label="Tutor suggested actions">
                    {message.suggested_actions.map((action) => <Button
                      className="h-auto min-h-10 rounded-full border border-[#b8ddd6] bg-white px-3 py-2 text-left text-sm text-[#245b55] hover:bg-[#e2f3ef]"
                      disabled={state === "sending"}
                      key={action}
                      onClick={() => void sendMessage(action, true)}
                      type="button"
                      variant="secondary"
                    >
                      <span dir="auto">{action}</span>
                    </Button>)}
                  </div> : null}
                </div>
                {!isTutor ? <ChatAvatar participant="Lina" /> : null}
              </article>
            );
          })}</div> : <div className="grid min-h-72 place-items-center px-4 text-center">
            <div className="max-w-sm">
              <div aria-hidden="true" className="mx-auto grid size-16 place-items-center rounded-[1.4rem] bg-[#e9f7f3] text-3xl text-[#328577]">✎</div>
              <h3 className="mt-5 font-display text-2xl text-ink">Welcome to Math</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">Start with a question, an answer you tried, or something you would like Tutor to explain.</p>
            </div>
          </div>}
        </div>
        <form className="rounded-[1.5rem] border border-[#e6e0f2] bg-white p-3 shadow-sm sm:grid sm:grid-cols-[1fr_auto] sm:items-center sm:gap-3 sm:p-4" onSubmit={send}>
          <label className="sr-only" htmlFor="student-math-message">Your Math question or attempt</label>
          <input
            id="student-math-message"
            dir="auto"
            className="h-12 w-full rounded-2xl bg-[#f8f7fb] px-4 text-sm text-ink outline-none ring-[#9c7ac9] transition focus:ring-2"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask a question or share what you tried"
            maxLength={4000}
          />
          <Button className="mt-3 w-full sm:mt-0 sm:w-auto" type="submit" disabled={!draft.trim() || state === "sending"}>
            {state === "sending" ? "Tutor is thinking…" : "Send"}
          </Button>
        </form>
        {error ? <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert"><span>{error}</span><Button type="button" variant="secondary" onClick={() => setLoadAttempt((attempt) => attempt + 1)}>Reload chat</Button></div> : null}
        <p className="text-center text-xs text-slate-500">Tutor will help you work through the next step.</p>
      </div>
    </section>
  );
}
