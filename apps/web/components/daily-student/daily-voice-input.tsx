"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { dailyPresentationCopy, type DailyPresentationCopy } from "@/lib/daily-presentation-copy";
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
  copy = dailyPresentationCopy("ltr").voice,
}: {
  apiBaseUrl: string;
  learningSessionId: string | null;
  draft: string;
  chatSending: boolean;
  getToken: () => Promise<string | null>;
  onTranscript: (transcript: string) => void;
  onActiveChange: (active: boolean) => void;
  copy?: DailyPresentationCopy["voice"];
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
      setVoiceError(copy.unsupported);
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
    <div className="flex min-h-12 items-center gap-2">
      {voiceState === "RECORDING" ? <>
        <Button type="button" variant="secondary" className="min-h-12 border border-rose-200 bg-rose-50 text-rose-900 focus-visible:ring-2 focus-visible:ring-rose-500" aria-label={copy.stop} onClick={() => void recorderRef.current?.stop()}><span aria-hidden="true">■</span><span className="ml-2 tabular-nums">{formatRecordingElapsed(recordingElapsed)}</span></Button>
        <Button type="button" variant="secondary" className="min-h-12 px-3 focus-visible:ring-2 focus-visible:ring-[#7d70df]" aria-label={copy.cancel} onClick={() => recorderRef.current?.cancel()}>{copy.cancel}</Button>
      </> : <Button type="button" variant="secondary" className="min-h-12 min-w-12 px-3 focus-visible:ring-2 focus-visible:ring-[#7d70df]" aria-label={availability.canStart ? copy.record : copy.unavailable} title={availability.canStart ? copy.record : copy.unavailable} disabled={!availability.canStart || !learningSessionId} onClick={start}><span aria-hidden="true">{voiceState === "TRANSCRIBING" ? "…" : "🎙"}</span><span className="sr-only">{voiceState === "REQUESTING_PERMISSION" ? copy.requestingPermission : voiceState === "TRANSCRIBING" ? copy.transcribing : copy.record}</span></Button>}
    </div>
    {voiceState !== "IDLE" || voiceError ? <p className="col-span-full text-xs text-slate-600" role="status" aria-live="polite">{voiceState === "REQUESTING_PERMISSION" ? copy.requestingPermission : voiceState === "RECORDING" ? copy.recording(formatRecordingElapsed(recordingElapsed)) : voiceState === "TRANSCRIBING" ? copy.transcribing : voiceError}</p> : null}
  </>;
}
