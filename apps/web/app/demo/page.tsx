"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { publicConfig } from "@/lib/public-config";

type Turn = { role: "student" | "tutor"; text: string; sources?: { source_ref: string; page_number: number | null }[]; intelligence?: string[] };
type Inspector = Record<string, unknown>;

const endpoint = (path: string) => `${publicConfig.apiBaseUrl}/v1/demo${path}`;

export default function SandboxDemoPage() {
  const [sessionId, setSessionId] = useState<string>();
  const [text, setText] = useState("I tried 3.452 × 10, but I need help moving the decimal point.");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [inspector, setInspector] = useState<Inspector>();
  const [status, setStatus] = useState("Preparing Sandbox/Test Learner…");

  const inspect = async () => {
    const response = await fetch(endpoint("/inspector"));
    if (response.ok) setInspector(await response.json() as Inspector);
  };
  const begin = async () => {
    await fetch(endpoint("/bootstrap"), { method: "POST" });
    const response = await fetch(endpoint("/sessions"), { method: "POST" });
    const payload = await response.json() as { session_id: string };
    setSessionId(payload.session_id); setTurns([]); setStatus("New Math session ready."); await inspect();
  };
  useEffect(() => { void begin(); }, []);
  const send = async (event: FormEvent) => {
    event.preventDefault(); if (!sessionId || !text.trim()) return;
    const studentText = text.trim(); setTurns((value) => [...value, { role: "student", text: studentText }]); setText("");
    const response = await fetch(endpoint(`/sessions/${sessionId}/turn`), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: studentText }) });
    const payload = await response.json() as { text: string; sources: Turn["sources"]; intelligence_used: string[] };
    setTurns((value) => [...value, { role: "tutor", text: payload.text, sources: payload.sources, intelligence: payload.intelligence_used }]); setStatus("Tutor response saved."); await inspect();
  };
  const close = async () => { if (!sessionId) return; await fetch(endpoint(`/sessions/${sessionId}/close`), { method: "POST" }); setStatus("Session closed and consolidated into Evidence and Intelligence."); await inspect(); };
  const reprocess = async () => { await fetch(endpoint("/reprocess"), { method: "POST" }); setStatus("A new derived intelligence version was rebuilt from preserved raw history."); await inspect(); };

  return <main className="min-h-screen bg-[#fffaf0] px-5 py-7 text-ink sm:px-8"><div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.1fr_.9fr]">
    <section className="rounded-[2rem] bg-white p-6 shadow-sm ring-1 ring-orange-100 sm:p-8"><p className="text-sm font-bold uppercase tracking-[.16em] text-orange-500">Development-only · Sandbox/Test Learner</p><h1 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Math Quest with Lina</h1><p className="mt-3 max-w-xl text-slate-600">Try the Grade 5 Eureka Math workbook. This is a safe test learner—not Lina’s real profile.</p>
      <div className="mt-6 grid gap-3">{turns.length === 0 ? <div className="rounded-2xl bg-violet-50 p-5 text-violet-900">Start with the suggested place-value answer, or ask a workbook question.</div> : turns.map((turn, index) => <article key={index} className={`rounded-2xl p-4 ${turn.role === "student" ? "ml-8 bg-sky text-slate-800" : "mr-4 bg-mint text-slate-800"}`}><p className="mb-1 text-xs font-bold uppercase tracking-wide opacity-60">{turn.role === "student" ? "You" : "Lina Tutor"}</p><p className="leading-6">{turn.text}</p>{turn.sources?.length ? <p className="mt-3 text-xs">Grounded in: {turn.sources.map((source) => source.source_ref).join(", ")}</p> : null}{turn.intelligence?.length ? <p className="mt-2 text-xs">Relevant compact memory used: {turn.intelligence.join(" ")}</p> : null}</article>)}</div>
      <form onSubmit={send} className="mt-6 flex gap-2"><input value={text} onChange={(event) => setText(event.target.value)} className="min-w-0 flex-1 rounded-full border border-slate-200 px-4 py-3" aria-label="Math question"/><Button type="submit" disabled={!sessionId}>Ask</Button></form>
      <div className="mt-4 flex flex-wrap gap-2"><Button type="button" variant="secondary" onClick={() => void close()} disabled={!sessionId}>Close & consolidate</Button><Button type="button" variant="secondary" onClick={() => void begin()}>Start later session</Button><Button type="button" variant="secondary" onClick={() => void reprocess()}>Rebuild intelligence</Button></div><p className="mt-3 text-sm text-slate-500" role="status">{status}</p>
    </section>
    <aside className="rounded-[2rem] bg-[#182033] p-6 text-white"><p className="text-sm font-bold uppercase tracking-[.16em] text-mint">Learning Intelligence Inspector</p><p className="mt-2 text-sm text-slate-300">Debug surface only; this is not the Parent Dashboard.</p><div className="mt-5 grid gap-3">{["documents", "candidate_events", "events", "evidence", "current_state", "patterns", "cards", "decision_views"].map((key) => <details key={key} className="rounded-xl bg-white/10 p-3"><summary className="cursor-pointer font-semibold">{key.replaceAll("_", " ")} ({Array.isArray(inspector?.[key]) ? (inspector?.[key] as unknown[]).length : 0})</summary><pre className="mt-3 overflow-auto whitespace-pre-wrap break-words text-xs text-slate-200">{JSON.stringify(inspector?.[key] ?? [], null, 2)}</pre></details>)}</div></aside>
  </div></main>;
}
