import React, { useState } from "react";
import { createRoot } from "react-dom/client";

import { DailySourceInput, StudentSourceCard, sourceMetadataFromFile } from "../../components/daily-student/daily-source-input";
import { DailyVoiceInput } from "../../components/daily-student/daily-voice-input";
import { buildDailySourceSubmission, type StudentSourceAsset } from "../../lib/daily-source";

let requests: Array<{ content: string; filename: string | null; sourceAssetId: string | null }> = [];
let previewBlob: Blob = new Blob();

class ProofRecorder {
  static isTypeSupported(type: string) { return type.startsWith("audio/webm"); }
  state: RecordingState = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  onstop: ((event: Event) => void) | null = null;
  start() { this.state = "recording"; }
  stop() { this.state = "inactive"; this.onstop?.(new Event("stop")); }
}
Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia: async () => ({ getTracks: () => [{ stop() {} }] }) } });
Object.assign(window, { MediaRecorder: ProofRecorder });
Object.assign(globalThis, { fetch: async () => new Response(previewBlob, { status: 200 }) });

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [active, setActive] = useState<StudentSourceAsset | null>(null);
  const [historySource, setHistorySource] = useState<StudentSourceAsset | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [voiceBusy, setVoiceBusy] = useState(false);
  return <main>
    <header><p>Daily learning</p><h1>Show Lina what you are working on.</h1></header>
    <section aria-label="Learning Chat">
      <h2>Learning Chat</h2>
      <form onSubmit={(event) => {
        event.preventDefault();
        if (!file && !active) return;
        const submission = buildDailySourceSubmission({ content: draft, file, activeSourceId: file ? null : active?.id ?? null });
        const source = submission.form.get("source");
        requests.push({ content: submission.studentContent, filename: source instanceof File ? source.name : null, sourceAssetId: submission.form.get("source_asset_id")?.toString() ?? null });
        if (file) {
          const durable = { ...sourceMetadataFromFile(file), id: "asset-proof", preview_url: "/preview" };
          previewBlob = file;
          setActive(durable);
          setHistorySource(durable);
        }
        setFile(null);
        setDraft("");
      }}>
        <DailySourceInput file={file} activeSource={active} disabled={false} onFile={setFile} onDismissActive={() => setActive(null)} onError={setError} />
        {file && !draft.trim() ? <p>Sending without a question will ask: “Help me with this.”</p> : null}
        <DailyVoiceInput apiBaseUrl="https://api.example.test" learningSessionId="proof-session" draft={draft} chatSending={false} getToken={async () => "proof-token"} onActiveChange={setVoiceBusy} onTranscript={setDraft} />
        <label htmlFor="message">Your message</label><input id="message" value={draft} onChange={(event) => setDraft(event.target.value)} />
        <button type="submit" disabled={voiceBusy || (!file && !draft.trim())}>Send</button>
      </form>
      <p role="alert">{error}</p>
      {historySource ? <article><strong>You</strong><p>Help me with this.</p><StudentSourceCard source={historySource} apiBaseUrl="https://api.example.test" getToken={async () => "proof-token"} /></article> : null}
    </section>
  </main>;
}

Object.assign(window, { sourceProof: { result: () => ({ requests }) } });
createRoot(document.getElementById("root")!).render(<App />);
