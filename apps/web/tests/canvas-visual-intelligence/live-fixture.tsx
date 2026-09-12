import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { StudioRendererHost } from "../../components/daily-student/studio-renderer-host";
import type { StudioSnapshotFrame } from "../../lib/studio/contracts";

function App() {
  const [snapshot, setSnapshot] = useState<StudioSnapshotFrame | null>(null);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState("");
  const runtime = new URLSearchParams(location.search).get("runtime");
  const refresh = async () => {
    const response = await fetch(`/api/v1/student/studio/${runtime}/snapshot`);
    if (!response.ok) throw new Error("Snapshot unavailable");
    setSnapshot(await response.json());
  };
  useEffect(() => { void refresh(); }, []);
  return <main className="visual-proof" dir={snapshot?.active_scene_contract?.direction ?? "auto"}><h1>Live Canvas acceptance</h1>
    <p>Production renderer, persisted Scene and server-owned Build.</p>
    <p role="status" data-live-result>{result}</p>
    {snapshot && <StudioRendererHost snapshot={snapshot} operationPending={pending}
      onReload={() => { void refresh(); }} onOperation={async operation => {
        setPending(true);
        try {
          const response = await fetch(`/api/v1/student/studio/${runtime}/operations`, {
            method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(operation),
          });
          if (!response.ok) throw new Error(await response.text());
          const saved = await response.json();
          setResult(`SAVED:${operation.action_key}:${saved.student_interaction_id ?? saved.event_id}`);
          if (saved.student_interaction_id) {
            const turn = await fetch(`/api/v1/student/studio/${runtime}/interactions/${saved.student_interaction_id}/turn/stream`, {method: "POST"});
            const stream = await turn.text();
            if (!turn.ok || !stream.includes("event: turn")) throw new Error("Tutor continuation failed");
            setResult(`COMPLETED:${operation.action_key}:${saved.student_interaction_id}`);
          }
          await refresh();
        } catch (error) { setResult(`FAILED:${String(error)}`); throw error; }
        finally { setPending(false); }
      }}/>}</main>;
}
createRoot(document.getElementById("root")!).render(<App/>);
