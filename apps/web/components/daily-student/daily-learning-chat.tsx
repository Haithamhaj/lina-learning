"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type {
  DailyLearningMessage,
  DailySendOptions,
  DailyTutorState,
} from "@/components/daily-student/use-daily-tutor-session";

type DailyLearningChatProps = {
  messages: DailyLearningMessage[];
  state: DailyTutorState;
  error: string;
  sendMessage: (content: string, options?: DailySendOptions) => Promise<void>;
  retryOpening: () => void;
};

function ParticipantMark({ participant }: { participant: "Lina" | "Tutor" }) {
  const isTutor = participant === "Tutor";

  return (
    <span
      aria-hidden="true"
      className={`grid size-8 shrink-0 place-items-center rounded-xl text-[0.68rem] font-bold shadow-[0_10px_18px_-13px_rgba(3,22,39,0.95)] ${isTutor ? "bg-[#bce8db] text-[#0d4250]" : "bg-[#d9cbff] text-[#44316e]"}`}
    >
      {isTutor ? "✦" : "L"}
    </span>
  );
}

function MessageBubble({ message, isStreaming }: { message: DailyLearningMessage; isStreaming: boolean }) {
  const isTutor = message.role === "tutor";
  const isThinking = isTutor && isStreaming && !message.content;
  const participant = isTutor ? "Tutor" : "Lina";

  return (
    <article className={`flex items-end gap-2.5 ${isTutor ? "justify-start" : "justify-end"}`}>
      {isTutor ? <ParticipantMark participant="Tutor" /> : null}
      <div className="max-w-[88%]">
        <p className={`mb-1 px-1 text-[0.65rem] font-bold uppercase tracking-[0.14em] ${isTutor ? "text-[#8ccabe]" : "text-right text-[#cbbdff]"}`}>{participant}</p>
        <div className={`rounded-[1.45rem] px-4 py-3.5 shadow-[0_18px_28px_-25px_rgba(0,0,0,0.95)] ${isTutor ? "rounded-bl-md border border-white/10 bg-white/[0.09] text-[#f4fcfa]" : "rounded-br-md border border-[#b19be0] bg-[linear-gradient(135deg,#8f70bf,#66508e)] text-white"}`}>
          {isThinking ? <p className="flex items-center gap-2 text-base leading-6"><span aria-hidden="true" className="flex gap-1"><span className="size-1.5 rounded-full bg-current opacity-45" /><span className="size-1.5 rounded-full bg-current opacity-70" /><span className="size-1.5 rounded-full bg-current" /></span>Tutor is thinking…</p> : <p dir="auto" className="whitespace-pre-wrap text-base leading-7">{message.content}</p>}
        </div>
      </div>
      {!isTutor ? <ParticipantMark participant="Lina" /> : null}
    </article>
  );
}

function OpeningState({ error, retryOpening }: Pick<DailyLearningChatProps, "error" | "retryOpening">) {
  return (
    <section aria-label="Studio conversation" className="grid min-h-[36rem] place-items-center overflow-hidden rounded-[2rem] border border-[#254958] bg-[linear-gradient(160deg,#0a2c3e_0%,#123b4d_48%,#183449_100%)] px-5 py-8 text-center shadow-[0_32px_75px_-45px_rgba(11,34,50,0.95)]" role="alert">
      <div className="max-w-sm">
        <span aria-hidden="true" className="mx-auto grid size-12 place-items-center rounded-2xl border border-white/15 bg-white/10 text-lg text-[#d9f7ef]">✦</span>
        <p className="mt-5 text-lg font-semibold tracking-[-0.025em] text-[#fff8f2]">Let’s open your studio again.</p>
        <p className="mt-2 text-base leading-6 text-[#f0c6c2]">{error}</p>
        <Button className="mt-5 rounded-xl bg-[#d7f4e9] px-4 text-[#123d48] hover:bg-white" onClick={retryOpening} type="button">Try again</Button>
      </div>
    </section>
  );
}

export function DailyLearningChat({ messages, state, error, sendMessage, retryOpening }: DailyLearningChatProps) {
  const [draft, setDraft] = useState("");
  const transcriptRef = useRef<HTMLDivElement>(null);
  const followLiveEdge = useRef(true);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript || !followLiveEdge.current) return;
    transcript.scrollTop = transcript.scrollHeight;
  }, [messages, state]);

  const send = (content: string) => {
    const nextContent = content.trim();
    if (!nextContent) return;
    setDraft("");
    void sendMessage(nextContent);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    send(draft);
  };

  if (state === "loading") {
    return <section aria-label="Studio conversation" className="grid min-h-[36rem] place-items-center rounded-[2rem] border border-[#254958] bg-[linear-gradient(160deg,#0a2c3e_0%,#123b4d_48%,#183449_100%)] px-5 text-center text-base text-[#c8e2dc] shadow-[0_32px_75px_-45px_rgba(11,34,50,0.95)]">Opening your learning studio…</section>;
  }

  if (state === "error" && messages.length === 0) return <OpeningState error={error} retryOpening={retryOpening} />;

  return (
    <section aria-label="Studio conversation" className="relative flex h-[min(72dvh,48rem)] min-h-[36rem] flex-col overflow-hidden rounded-[2rem] border border-[#254958] bg-[linear-gradient(160deg,#0a2c3e_0%,#123b4d_48%,#183449_100%)] shadow-[0_32px_75px_-45px_rgba(11,34,50,0.95)] lg:h-[calc(100dvh-10rem)] lg:min-h-0">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-44 bg-[radial-gradient(circle_at_10%_10%,rgba(130,191,178,0.28),transparent_48%),radial-gradient(circle_at_95%_0%,rgba(194,169,255,0.2),transparent_42%)]" />
      <div className="relative flex items-start justify-between border-b border-white/10 px-5 py-5">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.18em] text-[#a6dcd0]">Studio conversation</p>
          <p className="mt-1 text-base font-semibold tracking-[-0.02em] text-[#fffaf4]">Think it through with Tutor</p>
          <p className="mt-1 text-xs leading-5 text-[#b5cbcb]">Guidance stays close while the canvas holds the idea.</p>
        </div>
        <span aria-hidden="true" className="grid size-10 place-items-center rounded-2xl border border-white/10 bg-white/10 text-[#d9f7ef] shadow-lg">✦</span>
      </div>

      <div aria-label="Conversation transcript" aria-live="polite" aria-relevant="additions text" className="relative min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-5 sm:px-5" onScroll={(event) => { const element = event.currentTarget; followLiveEdge.current = element.scrollHeight - element.scrollTop - element.clientHeight < 72; }} ref={transcriptRef} role="log" tabIndex={0}>
        {messages.length === 0 ? <div className="grid min-h-[25rem] place-items-center text-center"><div className="max-w-[17rem]"><span aria-hidden="true" className="mx-auto grid size-14 place-items-center rounded-[1.2rem] border border-white/15 bg-white/10 text-xl text-[#d5f6ed] shadow-[0_18px_35px_-25px_rgba(0,0,0,0.9)]">✦</span><p className="mt-5 text-xl font-semibold tracking-[-0.04em] text-[#fffaf4]">What would you like to work through?</p><p className="mt-3 text-sm leading-6 text-[#bed0d0]">Ask a question, share an attempt, or name the step that feels unclear.</p></div></div> : messages.map((message) => <MessageBubble isStreaming={state === "streaming"} key={message.id} message={message} />)}
      </div>

      {state === "error" ? <div className="relative mx-4 mb-3 rounded-2xl border border-[#af7373] bg-[#56333e] px-4 py-3 text-sm leading-5 text-[#ffdad4] sm:mx-5" role="alert"><span dir="auto">{error}</span><p className="mt-1 text-[#f4c8c4]">Your message is still here. Write a new follow-up when you are ready.</p></div> : null}

      <form className="sticky bottom-0 z-10 border-t border-white/10 bg-[#0a2939]/95 p-3 shadow-[0_-16px_35px_-28px_rgba(0,0,0,0.95)] backdrop-blur-xl sm:p-4" onSubmit={submit}>
        <label className="sr-only" htmlFor="daily-learning-message">Your question or answer</label>
        <div className="flex gap-2 rounded-[1.45rem] border border-white/15 bg-white/[0.08] p-2 shadow-inner focus-within:ring-2 focus-within:ring-[#a5e4d3] focus-within:ring-offset-2 focus-within:ring-offset-[#0a2939]">
          <input aria-describedby={state === "streaming" ? "daily-streaming-status" : undefined} className="h-11 min-w-0 flex-1 bg-transparent px-3 text-base text-white outline-none placeholder:text-[#a4bec1]" dir="auto" id="daily-learning-message" maxLength={4000} onChange={(event) => setDraft(event.target.value)} placeholder="Ask a question or share what you tried" value={draft} />
          <Button className="rounded-xl bg-[linear-gradient(135deg,#d8f4e8,#b9e6d8)] px-4 font-semibold text-[#113d49] shadow-[0_10px_18px_-13px_rgba(143,234,208,0.85)] hover:bg-white" disabled={!draft.trim() || state === "streaming"} type="submit">Send</Button>
        </div>
        {state === "streaming" ? <p className="px-3 pt-2 text-sm text-[#b5d4cd]" id="daily-streaming-status">Tutor is preparing the next step.</p> : null}
      </form>
    </section>
  );
}
