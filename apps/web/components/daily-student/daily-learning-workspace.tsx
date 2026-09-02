import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type {
  DailyLearningMessage,
  DailySendOptions,
  DailyTutorState,
} from "@/components/daily-student/use-daily-tutor-session";

type DailyLearningWorkspaceProps = {
  messages: DailyLearningMessage[];
  state: DailyTutorState;
  error: string;
  sendMessage: (content: string, options?: DailySendOptions) => Promise<void>;
};

function latestMessage(messages: DailyLearningMessage[], role: DailyLearningMessage["role"]) {
  return [...messages].reverse().find((message) => message.role === role);
}

type Equation = { left: string; operator: string; right: string; result: string };

function equationFrom(content?: string): Equation | null {
  const match = content?.match(/(\d{1,4})\s*([+−-])\s*(\d{1,4})\s*=\s*(\d{1,5})(?!\s*[+−-])/);
  if (!match) return null;
  return { left: match[1], operator: match[2], right: match[3], result: match[4] };
}

function CanvasNote({ label, children, tone }: { label: string; children: ReactNode; tone: "question" | "guidance" }) {
  const classes = tone === "question"
    ? "border-[#e1d5ff] bg-[#fbf9ff] text-[#42345f]"
    : "border-[#bce3d5] bg-[#f5fcf9] text-[#153e46]";

  return (
    <section className={`rounded-[1.35rem] border p-4 shadow-[0_18px_35px_-32px_rgba(24,45,65,0.75)] ${classes}`}>
      <p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] opacity-65">{label}</p>
      <div className="mt-2 text-[0.95rem] leading-6">{children}</div>
    </section>
  );
}

function ArithmeticSketch({ equation }: { equation: Equation }) {
  return (
    <section aria-label="Visual reasoning map" className="relative overflow-hidden rounded-[1.55rem] border border-[#dce4ec] bg-[linear-gradient(145deg,#fbfdff_0%,#f5f7ff_52%,#fbfbf7_100%)] p-4 shadow-[0_24px_46px_-38px_rgba(24,48,72,0.85)] sm:p-5">
      <div aria-hidden="true" className="absolute -right-12 -top-16 size-44 rounded-full bg-[#e6ddff]/70 blur-2xl" />
      <div aria-hidden="true" className="absolute -bottom-16 left-1/3 size-44 rounded-full bg-[#cbeee1]/65 blur-2xl" />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-[#596983]">Visual reasoning map</p>
          <p className="mt-1 text-sm font-semibold text-[#243c58]">Tutor's shown step</p>
        </div>
        <span className="rounded-full border border-[#dde7ed] bg-white/75 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-[#5c7180]">From guidance</span>
      </div>
      <svg aria-label={`${equation.left} ${equation.operator} ${equation.right} equals ${equation.result}`} className="relative mt-4 h-[8.7rem] w-full" role="img" viewBox="0 0 680 150">
        <defs>
          <linearGradient id="daily-studio-question" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#F0EAFE" /><stop offset="1" stopColor="#DDD0FB" /></linearGradient>
          <linearGradient id="daily-studio-guidance" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#DDF4EC" /><stop offset="1" stopColor="#BDE7D8" /></linearGradient>
          <linearGradient id="daily-studio-result" x1="0" x2="1" y1="0" y2="1"><stop stopColor="#FFF1DF" /><stop offset="1" stopColor="#FED7AF" /></linearGradient>
        </defs>
        <path d="M152 77H235M432 77H515" fill="none" stroke="#AEC2D2" strokeDasharray="5 8" strokeWidth="3" />
        <path d="M222 68L239 77L222 86M502 68L519 77L502 86" fill="none" stroke="#758BA1" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
        <circle cx="99" cy="77" fill="url(#daily-studio-question)" r="53" />
        <circle cx="340" cy="77" fill="url(#daily-studio-guidance)" r="53" />
        <circle cx="581" cy="77" fill="url(#daily-studio-result)" r="53" />
        <text fill="#5B477E" fontSize="13" fontWeight="700" textAnchor="middle" x="99" y="60">START</text>
        <text fill="#5B477E" fontSize="29" fontWeight="700" textAnchor="middle" x="99" y="91">{equation.left}</text>
        <text fill="#276258" fontSize="13" fontWeight="700" textAnchor="middle" x="340" y="60">STEP</text>
        <text fill="#276258" fontSize="29" fontWeight="700" textAnchor="middle" x="340" y="91">{equation.operator} {equation.right}</text>
        <text fill="#8A5026" fontSize="13" fontWeight="700" textAnchor="middle" x="581" y="60">RESULT</text>
        <text fill="#8A5026" fontSize="29" fontWeight="700" textAnchor="middle" x="581" y="91">{equation.result}</text>
      </svg>
      <p className="relative text-xs leading-5 text-[#65788a]">This visual only arranges the exact equation Tutor included in the current guidance.</p>
    </section>
  );
}

function ConversationMap({ question, guidance, isStreaming }: { question: string; guidance: string; isStreaming: boolean }) {
  return (
    <section aria-label="Visual reasoning map" className="relative overflow-hidden rounded-[1.55rem] border border-[#dce4ec] bg-[linear-gradient(145deg,#fbfdff_0%,#f5f7ff_52%,#fbfbf7_100%)] p-4 shadow-[0_24px_46px_-38px_rgba(24,48,72,0.85)] sm:p-5">
      <div aria-hidden="true" className="absolute -right-12 -top-16 size-44 rounded-full bg-[#e6ddff]/70 blur-2xl" />
      <div aria-hidden="true" className="absolute -bottom-16 left-1/3 size-44 rounded-full bg-[#cbeee1]/65 blur-2xl" />
      <div className="relative flex items-center justify-between gap-3">
        <div><p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-[#596983]">Visual reasoning map</p><p className="mt-1 text-sm font-semibold text-[#243c58]">Tutor's shown step</p></div>
        <span className="rounded-full border border-[#dde7ed] bg-white/75 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-[#5c7180]">Current turn</span>
      </div>
      <div className="relative mt-4 grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <div className="rounded-[1.2rem] border border-[#e1d5ff] bg-[#fcfaff] p-3 text-sm leading-5 text-[#4c3a72]"><p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-[#806aa8]">Question</p><p dir="auto" className="mt-1.5 line-clamp-4 font-medium">{question}</p></div>
        <span aria-hidden="true" className="mx-auto grid size-9 place-items-center rounded-full border border-[#c8d8de] bg-white text-[#5a7481] shadow-sm">→</span>
        <div className="rounded-[1.2rem] border border-[#bce3d5] bg-[#f4fcf8] p-3 text-sm leading-5 text-[#24534e]"><p className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-[#4b8a7b]">{isStreaming ? "Taking shape" : "Tutor guidance"}</p><p dir="auto" className="mt-1.5 line-clamp-4">{guidance}</p></div>
      </div>
      <p className="relative mt-3 text-xs leading-5 text-[#65788a]">The canvas organizes this turn; it does not add an answer of its own.</p>
    </section>
  );
}

function LearningPath({ readyForNextStep }: { readyForNextStep: boolean }) {
  const steps = ["Question", "Tutor guide", "Your next move"];
  return (
    <section aria-label="where we are now" className="rounded-[1.3rem] border border-[#e5e3dd] bg-white/72 px-4 py-3 shadow-[0_14px_28px_-28px_rgba(24,45,65,0.8)]">
      <p className="text-[0.65rem] font-bold uppercase tracking-[0.15em] text-[#70777e]">Where we are now</p>
      <ol className="mt-3 flex items-center gap-2 overflow-x-auto pb-1 text-xs font-semibold text-[#50616d]">
        {steps.map((step, index) => <li className="flex shrink-0 items-center gap-2" key={step}><span className={`grid size-7 place-items-center rounded-full ${index === 0 ? "bg-[#e8ddff] text-[#553f80]" : index === 1 ? "bg-[#dff3eb] text-[#27665b]" : readyForNextStep ? "bg-[#ffe2bf] text-[#81502d]" : "bg-[#edf0f1] text-[#77838c]"}`}>{index + 1}</span><span>{step}</span>{index < steps.length - 1 ? <span aria-hidden="true" className="h-px w-5 bg-[#d6dde0]" /> : null}</li>)}
      </ol>
    </section>
  );
}

export function DailyLearningWorkspace({ messages, state, error, sendMessage }: DailyLearningWorkspaceProps) {
  const latestStudentMessage = latestMessage(messages, "student");
  const latestTutorMessage = latestMessage(messages, "tutor");
  const isStreaming = state === "streaming";
  const latestActions = latestTutorMessage?.suggested_actions ?? [];
  const guidedCheck = latestTutorMessage?.guided_check;
  const equation = equationFrom(latestTutorMessage?.content);
  const question = latestStudentMessage?.content ?? "";
  const guidance = latestTutorMessage?.content || (isStreaming ? "Tutor is building the next explanation…" : "Tutor guidance will appear here after the next turn.");

  return (
    <aside aria-label="Active learning workspace" className="relative min-w-0 overflow-hidden rounded-[2rem] border border-white/90 bg-white/75 p-4 shadow-[0_32px_78px_-48px_rgba(22,45,65,0.75)] backdrop-blur-xl sm:p-5 lg:p-6">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-32 -top-36 size-[26rem] rounded-full bg-[#e6dcff]/80 blur-3xl" />
        <div className="absolute -bottom-44 left-[12%] size-[25rem] rounded-full bg-[#d8f3e6]/70 blur-3xl" />
        <svg className="absolute inset-0 size-full opacity-[0.38]" fill="none" viewBox="0 0 900 680"><path d="M-30 480C170 350 290 560 480 389C620 264 718 310 940 148" stroke="#B9CAE0" strokeDasharray="6 13" strokeWidth="2" /><path d="M-12 154C178 236 278 101 434 188C575 267 711 179 924 243" stroke="#B9DFCF" strokeDasharray="4 14" strokeWidth="2" /></svg>
      </div>

      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-[0.68rem] font-bold uppercase tracking-[0.18em] text-[#68588f]">Studio canvas</p>
          <h1 className="mt-1 text-[1.45rem] font-semibold tracking-[-0.045em] text-[#162f4b] sm:text-[1.7rem]">Make the thinking visible.</h1>
          <p className="mt-1 text-sm text-[#687987]">A living view of this learning turn.</p>
        </div>
        <span className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-semibold shadow-sm ${isStreaming ? "border-[#c7dceb] bg-[#edf7fc] text-[#327085]" : "border-[#dfe5dc] bg-white/85 text-[#65716a]"}`}>{isStreaming ? "Tutor is building" : "Active workspace"}</span>
      </div>

      {messages.length === 0 ? <section className="relative mt-5 grid min-h-[30rem] place-items-center overflow-hidden rounded-[1.75rem] border border-[#e0e4e7] bg-[linear-gradient(145deg,rgba(255,255,255,0.91),rgba(248,249,253,0.78))] p-6 text-center"><div aria-hidden="true" className="absolute inset-x-[12%] top-[26%] h-px bg-[linear-gradient(90deg,transparent,#d8d0ef,transparent)]" /><div className="relative max-w-md"><span aria-hidden="true" className="mx-auto grid size-16 place-items-center rounded-[1.4rem] border border-[#d7e8e2] bg-[#edf9f4] text-xl text-[#246258] shadow-[0_18px_35px_-23px_rgba(39,101,88,0.5)]">✦</span><p className="mt-5 text-xl font-semibold tracking-[-0.04em] text-[#1b344d]">Your first question gives this canvas a focus.</p><p className="mt-3 text-sm leading-6 text-[#687a88]">The Studio will keep your question, Tutor's guidance, and the next learning move together in one place.</p><div aria-hidden="true" className="mx-auto mt-7 grid max-w-sm grid-cols-3 gap-2 text-left"><span className="rounded-xl border border-[#e3dbf3] bg-white/70 px-3 py-2 text-[0.65rem] font-bold uppercase tracking-[0.11em] text-[#75628f]">Question</span><span className="rounded-xl border border-[#d7ebe3] bg-white/70 px-3 py-2 text-[0.65rem] font-bold uppercase tracking-[0.11em] text-[#4c8075]">Guidance</span><span className="rounded-xl border border-[#f0dfcb] bg-white/70 px-3 py-2 text-[0.65rem] font-bold uppercase tracking-[0.11em] text-[#8a6849]">Next move</span></div></div></section> : <div className="relative mt-5 space-y-4">
        <section aria-label="Current learning focus" className="rounded-[1.5rem] border border-[#e1d5ff] bg-[linear-gradient(135deg,rgba(249,247,255,0.96),rgba(255,255,255,0.86))] p-4 shadow-[0_20px_36px_-31px_rgba(61,40,112,0.7)]"><p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-[#725c9f]">Current learning focus</p><p dir="auto" className="mt-2 max-w-3xl whitespace-pre-wrap text-lg font-medium leading-7 tracking-[-0.02em] text-[#3f3262]">{question}</p></section>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.06fr)_minmax(19rem,0.94fr)]">
          <div className="space-y-4">
            {equation ? <ArithmeticSketch equation={equation} /> : <ConversationMap guidance={guidance} isStreaming={isStreaming} question={question} />}
            <LearningPath readyForNextStep={Boolean(guidedCheck || latestActions.length)} />
          </div>
          <div className="space-y-4">
            <CanvasNote label={isStreaming ? "Tutor is building" : "Tutor guidance"} tone="guidance"><p dir="auto" className="whitespace-pre-wrap">{guidance}</p></CanvasNote>
            <CanvasNote label="Question on the board" tone="question"><p dir="auto" className="whitespace-pre-wrap">{question}</p></CanvasNote>
          </div>
        </div>
      </div>}

      {guidedCheck ? <section aria-label="Guided learning check" className="relative mt-4 rounded-[1.45rem] border border-[#d9d0f0] bg-[linear-gradient(135deg,rgba(249,246,255,0.96),rgba(255,255,255,0.86))] p-4 shadow-[0_20px_35px_-30px_rgba(62,47,100,0.72)]"><div className="flex items-center justify-between gap-3"><p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-[#67518e]">Guided check</p><span className="rounded-full bg-[#ebe3fb] px-2.5 py-1 text-[0.62rem] font-bold uppercase tracking-[0.11em] text-[#685189]">From Tutor</span></div><p dir="auto" className="mt-2 text-base font-semibold leading-6 text-[#3a2b59]">{guidedCheck.prompt}</p><div className="mt-3 flex flex-wrap gap-2">{guidedCheck.choices.map((choice) => <Button className="h-auto min-h-10 rounded-xl border border-[#d2c5ed] bg-white px-3 py-2 text-sm text-[#45316a] shadow-sm hover:bg-[#f0ebfb]" key={`${guidedCheck.id}:${choice.label}`} onClick={() => void sendMessage(choice.label, { guidedCheckId: guidedCheck.id })} type="button" variant="secondary"><span dir="auto">{choice.label}</span></Button>)}</div></section> : null}

      {!guidedCheck && latestActions.length > 0 ? <section aria-label="Tutor next steps" className="relative mt-4 rounded-[1.45rem] border border-[#cde7dc] bg-[linear-gradient(135deg,rgba(244,252,248,0.97),rgba(255,255,255,0.87))] p-4 shadow-[0_20px_35px_-30px_rgba(34,93,77,0.55)]"><p className="text-[0.65rem] font-bold uppercase tracking-[0.16em] text-[#367468]">Choose a next step</p><div className="mt-3 flex flex-wrap gap-2">{latestActions.map((action) => <Button className="h-auto min-h-10 rounded-xl border border-[#b9ddd1] bg-white px-3 py-2 text-left text-sm text-[#1d5a52] shadow-sm hover:bg-[#eaf6f1]" key={`${action.kind}:${action.label}`} onClick={() => void sendMessage(action.label, { suggestedAction: true, suggestedActionKind: action.kind })} type="button" variant="secondary"><span dir="auto">{action.label}</span></Button>)}</div></section> : null}

      {state === "error" ? <p className="relative mt-4 rounded-xl border border-[#f0d4d1] bg-[#fff7f5] px-3 py-2 text-sm text-[#8a3d38]" dir="auto" role="alert">{error || "The last response did not finish. Your question remains visible; write a new follow-up when you are ready."}</p> : null}
    </aside>
  );
}
