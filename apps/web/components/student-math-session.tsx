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
};

type MathSession = {
  id: string;
  subject: "MATH";
  status: "OPEN";
  messages: Message[];
};

type TutorTurn = {
  text: string;
};

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
  }, [getToken, isLoaded]);

  const send = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = draft.trim();
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
        messages: [...current.messages, { id: studentId, role: "student", content, created_at: now }, { id: tutorId, role: "tutor", content: "", created_at: now }],
      } : current);
      setDraft("");
      const response = await fetch(`${publicConfig.apiBaseUrl}/v1/student/math/session/${learningSession.id}/turn/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content }),
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
              messages: current.messages.map((message) => message.id === tutorId ? { ...message, content: turn.text } : message),
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

  if (state === "loading") {
    return <p className="rounded-2xl bg-white p-5 text-sm text-slate-600">Opening your Math session…</p>;
  }
  if (state === "error" && !learningSession) {
    return <p className="rounded-2xl bg-white p-5 text-sm text-red-700" role="alert">{error}</p>;
  }

  return (
    <section aria-label="Math learning session" className="grid gap-4 rounded-3xl bg-white p-5 shadow-sm sm:p-6">
      <div>
        <h2 className="font-display text-2xl text-ink">Math</h2>
        <p className="mt-1 text-sm text-slate-600">Pick up where you left off. Your work stays in this learning session.</p>
      </div>
      <div className="grid max-h-80 gap-3 overflow-y-auto rounded-2xl bg-[#f5f7fb] p-4" aria-live="polite">
        {learningSession?.messages.length ? learningSession.messages.map((message) => (
          <p className="rounded-xl bg-white px-3 py-2 text-sm text-slate-700" key={message.id}>
            <span className="font-semibold text-ink">{message.role === "tutor" ? "Lina: " : "You: "}</span>{message.content || "…"}
          </p>
        )) : <p className="text-sm text-slate-600">What Math idea would you like to work on?</p>}
      </div>
      <form className="grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={send}>
        <label className="sr-only" htmlFor="student-math-message">Your Math question or attempt</label>
        <input
          id="student-math-message"
          className="rounded-xl border border-slate-200 px-4 py-3 text-sm text-ink"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Share a question or show what you tried"
          maxLength={4000}
          disabled={state === "sending"}
        />
        <Button type="submit" disabled={!draft.trim() || state === "sending"}>
          {state === "sending" ? "Lina is thinking…" : "Send"}
        </Button>
      </form>
      {error ? <p className="text-sm text-red-700" role="alert">{error}</p> : null}
      <p className="text-xs text-slate-500">Lina replies as she works through the next step with you.</p>
    </section>
  );
}
