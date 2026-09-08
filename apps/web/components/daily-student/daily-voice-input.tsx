"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DailyVoiceRecorder,
  formatRecordingElapsed,
  transcribeDailyRecording,
  voiceControlAvailability,
  type VoiceRecorderState,
} from "@/lib/daily-voice-recorder";

export function DailyVoiceInput({
  apiBaseUrl,
  learningSessionId,
  draft,
  chatSending,
  getToken,
  onTranscript,
  onActiveChange,
}: {
  apiBaseUrl: string;
  learningSessionId: string | null;
  draft: string;
  chatSending: boolean;
  getToken: () => Promise<string | null>;
  onTranscript: (transcript: string) => void;
  onActiveChange: (active: boolean) => void;
}) {
  const [voiceState, setVoiceState] = useState<VoiceRecorderState>("IDLE");
  const [recordingElapsed, setRecordingElapsed] = useState(0);
  const [voiceError, setVoiceError] = useState("");
  const recorderRef = useRef<DailyVoiceRecorder | null>(null);

  useEffect(() => () => recorderRef.current?.dispose(), []);

  const availability = voiceControlAvailability({ state: voiceState, draft, chatSending });
  const start = () => {
    if (!learningSessionId || !availability.canStart) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceError("Voice recording is not supported in this browser. You can keep typing.");
      return;
    }
    recorderRef.current?.dispose();
    const recorder = new DailyVoiceRecorder({
      requestStream: () => navigator.mediaDevices.getUserMedia({ audio: true }),
      createRecorder: (stream, mimeType) => new MediaRecorder(stream as MediaStream, {
        mimeType,
        audioBitsPerSecond: 32_000,
      }),
      transcribe: async (audio) => (await transcribeDailyRecording({
        apiBaseUrl,
        learningSessionId,
        audio,
        getToken,
      })).text,
      onStateChange: (state) => {
        setVoiceState(state);
        onActiveChange(state !== "IDLE");
      },
      onElapsedChange: setRecordingElapsed,
      onTranscript,
      onError: setVoiceError,
    });
    recorderRef.current = recorder;
    void recorder.start();
  };

  return <>
    <div className="order-1 flex min-h-12 items-center gap-2">
      {voiceState === "RECORDING" ? <>
        <Button type="button" variant="secondary" className="min-h-12 border border-rose-200 bg-rose-50 text-rose-900 focus-visible:ring-2 focus-visible:ring-rose-500" aria-label="Stop recording and transcribe" onClick={() => void recorderRef.current?.stop()}><span aria-hidden="true">■</span><span className="ml-2 tabular-nums">{formatRecordingElapsed(recordingElapsed)}</span></Button>
        <Button type="button" variant="secondary" className="min-h-12 px-3 focus-visible:ring-2 focus-visible:ring-[#7d70df]" aria-label="Cancel recording" onClick={() => recorderRef.current?.cancel()}>Cancel</Button>
      </> : <Button type="button" variant="secondary" className="min-h-12 min-w-12 px-3 focus-visible:ring-2 focus-visible:ring-[#7d70df]" aria-label={availability.reason} title={availability.reason} disabled={!availability.canStart || !learningSessionId} onClick={start}><span aria-hidden="true">{voiceState === "TRANSCRIBING" ? "…" : "🎙"}</span><span className="sr-only">{voiceState === "REQUESTING_PERMISSION" ? "Requesting microphone permission" : voiceState === "TRANSCRIBING" ? "Transcribing recording" : availability.reason}</span></Button>}
    </div>
    <p className="order-4 text-xs text-slate-600 sm:col-span-3" role="status" aria-live="polite">{voiceState === "REQUESTING_PERMISSION" ? "Requesting microphone permission…" : voiceState === "RECORDING" ? `Recording ${formatRecordingElapsed(recordingElapsed)}. Stop when you are ready.` : voiceState === "TRANSCRIBING" ? "Transcribing your recording…" : voiceError || "Type a message or record one, then review it before sending."}</p>
  </>;
}
