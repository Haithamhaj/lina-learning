import React, { useState } from "react";
import { createRoot } from "react-dom/client";

import { DailyVoiceInput } from "../../components/daily-student/daily-voice-input";

let transcriptionRequests = 0;
let submittedMessages: string[] = [];
let stoppedTracks = 0;
let completeTranscription: (() => void) | null = null;

class ProofTrack {
  stop() { stoppedTracks += 1; }
}

class ProofMediaRecorder {
  static isTypeSupported(type: string) { return type.startsWith("audio/webm"); }
  state: RecordingState = "inactive";
  mimeType: string;
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  onstop: ((event: Event) => void) | null = null;

  constructor(_stream: MediaStream, options?: MediaRecorderOptions) {
    this.mimeType = options?.mimeType ?? "audio/webm";
  }

  start() { this.state = "recording"; }
  stop() {
    if (this.state === "inactive") return;
    this.state = "inactive";
    this.ondataavailable?.(new BlobEvent("dataavailable", { data: new Blob(["proof-audio"], { type: this.mimeType }) }));
    this.onstop?.(new Event("stop"));
  }
}

Object.defineProperty(navigator, "mediaDevices", {
  configurable: true,
  value: { getUserMedia: async () => ({ getTracks: () => [new ProofTrack()] }) },
});
Object.assign(window, { MediaRecorder: ProofMediaRecorder });
Object.assign(globalThis, {
  fetch: async (_input: RequestInfo | URL, init?: RequestInit) => {
    transcriptionRequests += 1;
    if (!(init?.body instanceof FormData) || !(init.body.get("audio") instanceof Blob)) {
      return new Response(JSON.stringify({ detail: "missing audio" }), { status: 422 });
    }
    await new Promise<void>((resolve) => { completeTranscription = resolve; });
    return new Response(JSON.stringify({
      transcript: "What is one half?",
      transcription_execution_id: "proof-execution",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  },
});

function App() {
  const [draft, setDraft] = useState("");
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [, refresh] = useState(0);
  return <main>
    <header><p>Daily learning</p><h1>A calm place to think out loud.</h1></header>
    <section aria-label="Learning Chat">
      <h2>Learning Chat</h2>
      <form onSubmit={(event) => {
        event.preventDefault();
        if (!draft.trim() || voiceBusy) return;
        submittedMessages = [...submittedMessages, draft.trim()];
        setDraft("");
        refresh((value) => value + 1);
      }}>
        <DailyVoiceInput apiBaseUrl="https://api.example.test" learningSessionId="proof-session" draft={draft} chatSending={false} getToken={async () => "proof-token"} onActiveChange={setVoiceBusy} onTranscript={setDraft} />
        <label htmlFor="daily-learning-message">Your message for Tutor</label>
        <input id="daily-learning-message" dir="auto" value={draft} disabled={voiceBusy} onChange={(event) => setDraft(event.target.value)} />
        <button type="submit" disabled={!draft.trim() || voiceBusy}>Send</button>
      </form>
      <output data-submissions>{submittedMessages.join(" | ") || "No Student message"}</output>
    </section>
  </main>;
}

Object.assign(window, {
  voiceProof: {
    completeTranscription: () => completeTranscription?.(),
    result: () => ({ transcriptionRequests, submittedMessages, stoppedTracks }),
  },
});

createRoot(document.getElementById("root")!).render(<App />);
