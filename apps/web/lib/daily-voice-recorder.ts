export type VoiceRecorderState = "IDLE" | "REQUESTING_PERMISSION" | "RECORDING" | "TRANSCRIBING";

type TrackLike = { stop: () => void; readyState?: MediaStreamTrackState; enabled?: boolean; muted?: boolean };
type StreamLike = { getTracks: () => TrackLike[]; getAudioTracks?: () => TrackLike[] };
export type VoiceSignalMonitor = { hasNonSilentSignal: () => boolean | null; stop: () => void };
type RecorderLike = {
  state: RecordingState;
  mimeType: string;
  ondataavailable: ((event: BlobEvent) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
  onstop: ((event: Event) => void) | null;
  start: () => void;
  stop: () => void;
};

export type VoiceRecorderMessages = {
  unsupported: string;
  recordingStopped: string;
  permissionDenied: string;
  openFailed: string;
  microphoneUnavailable: string;
  noSpeechCaptured: string;
  noSpeechHeard: string;
  transcriptionFailed: string;
};

type VoiceAvailabilityCopy = {
  record: string;
  sendOrClear: string;
  waitForTutor: string;
  alreadyActive: string;
};

const defaultMessages: VoiceRecorderMessages = {
  unsupported: "Voice recording is not supported in this browser.",
  recordingStopped: "Voice recording stopped unexpectedly. Please try again.",
  permissionDenied: "Microphone permission was denied. You can keep typing or allow microphone access and try again.",
  openFailed: "The microphone could not be opened. You can keep typing and try again.",
  microphoneUnavailable: "The microphone is not sending audio. Check it and try again.",
  noSpeechCaptured: "No speech was captured. Please record again.",
  noSpeechHeard: "We could not hear any speech. Please record again.",
  transcriptionFailed: "The recording could not be transcribed. Please try again.",
};

const defaultAvailabilityCopy: VoiceAvailabilityCopy = {
  record: "Record a message",
  sendOrClear: "Send or clear your typed message before recording.",
  waitForTutor: "Wait for Tutor before recording.",
  alreadyActive: "Voice input is already active.",
};

type VoiceRecorderDependencies = {
  requestStream: () => Promise<StreamLike>;
  createRecorder: (stream: StreamLike, mimeType: string) => RecorderLike;
  createSignalMonitor?: (stream: StreamLike) => VoiceSignalMonitor | null;
  isTypeSupported?: (mimeType: string) => boolean;
  transcribe: (audio: Blob, signal: AbortSignal) => Promise<string>;
  now?: () => number;
  setInterval?: (callback: () => void, milliseconds: number) => number;
  clearInterval?: (id: number) => void;
  setTimeout?: (callback: () => void, milliseconds: number) => number;
  clearTimeout?: (id: number) => void;
  onStateChange: (state: VoiceRecorderState) => void;
  onElapsedChange: (seconds: number) => void;
  onTranscript: (transcript: string) => void;
  onError: (message: string) => void;
  messages?: VoiceRecorderMessages;
};

export function preferredRecordingMimeType(isSupported: (mimeType: string) => boolean): string | null {
  for (const mimeType of ["audio/webm;codecs=opus", "audio/webm"]) {
    if (isSupported(mimeType)) return mimeType;
  }
  return null;
}

export function formatRecordingElapsed(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(seconds / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  const remainder = seconds % 60;
  const clock = `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  return hours > 0 ? `${hours}:${clock}` : clock;
}

export function voiceControlAvailability({
  state,
  draft,
  chatSending,
  copy = defaultAvailabilityCopy,
}: {
  state: VoiceRecorderState;
  draft: string;
  chatSending: boolean;
  copy?: VoiceAvailabilityCopy;
}): { canStart: boolean; reason: string } {
  if (draft.trim()) return { canStart: false, reason: copy.sendOrClear };
  if (chatSending) return { canStart: false, reason: copy.waitForTutor };
  if (state !== "IDLE") return { canStart: false, reason: copy.alreadyActive };
  return { canStart: true, reason: copy.record };
}

function stopTracks(stream: StreamLike | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

function hasUsableAudioTrack(stream: StreamLike): boolean {
  const audioTracks = stream.getAudioTracks?.();
  if (!audioTracks) return true; // Non-browser test streams may not expose track details.
  return audioTracks.some((track) => track.readyState !== "ended" && track.enabled !== false && track.muted !== true);
}

export class DailyVoiceRecorder {
  private readonly dependencies: VoiceRecorderDependencies;
  private state: VoiceRecorderState = "IDLE";
  private stream: StreamLike | null = null;
  private recorder: RecorderLike | null = null;
  private chunks: Blob[] = [];
  private timer: number | null = null;
  private startedAt = 0;
  private cancelled = false;
  private disposed = false;
  private requestVersion = 0;
  private stopPromise: Promise<void> | null = null;
  private transcriptionAbort: AbortController | null = null;
  private signalMonitor: VoiceSignalMonitor | null = null;

  private get messages(): VoiceRecorderMessages {
    return this.dependencies.messages ?? defaultMessages;
  }

  constructor(dependencies: VoiceRecorderDependencies) {
    this.dependencies = dependencies;
  }

  async start(): Promise<void> {
    if (this.disposed || this.state !== "IDLE") return;
    const requestVersion = ++this.requestVersion;
    this.setState("REQUESTING_PERMISSION");
    this.dependencies.onElapsedChange(0);
    this.dependencies.onError("");
    try {
      const stream = await this.dependencies.requestStream();
      if (this.disposed || requestVersion !== this.requestVersion) {
        stopTracks(stream);
        return;
      }
      if (!hasUsableAudioTrack(stream)) {
        stopTracks(stream);
        this.setState("IDLE");
        this.dependencies.onError(this.messages.microphoneUnavailable);
        return;
      }
      const mimeType = preferredRecordingMimeType(
        this.dependencies.isTypeSupported ?? ((type) => MediaRecorder.isTypeSupported(type)),
      );
      if (!mimeType) {
        stopTracks(stream);
        this.setState("IDLE");
        this.dependencies.onError(this.messages.unsupported);
        return;
      }
      this.stream = stream;
      this.cancelled = false;
      this.chunks = [];
      const recorder = this.dependencies.createRecorder(stream, mimeType);
      this.recorder = recorder;
      try {
        this.signalMonitor = this.dependencies.createSignalMonitor?.(stream) ?? null;
      } catch {
        this.signalMonitor = null; // Recorder and provider remain available if signal analysis is unsupported.
      }
      recorder.ondataavailable = (event) => {
        if (!this.cancelled && event.data.size > 0) this.chunks.push(event.data);
      };
      recorder.onerror = () => this.failRecording(this.messages.recordingStopped);
      recorder.onstop = () => this.failRecording(this.messages.recordingStopped);
      recorder.start();
      this.startedAt = (this.dependencies.now ?? Date.now)();
      this.timer = (this.dependencies.setInterval ?? window.setInterval)(() => {
        const elapsed = Math.max(0, Math.floor(((this.dependencies.now ?? Date.now)() - this.startedAt) / 1_000));
        this.dependencies.onElapsedChange(elapsed);
      }, 1_000);
      this.setState("RECORDING");
    } catch (error) {
      if (this.disposed || requestVersion !== this.requestVersion) return;
      this.clearTimer();
      this.clearSignalMonitor();
      stopTracks(this.stream);
      this.stream = null;
      this.recorder = null;
      this.chunks = [];
      this.setState("IDLE");
      const denied = error instanceof DOMException && error.name === "NotAllowedError";
      this.dependencies.onError(denied ? this.messages.permissionDenied : this.messages.openFailed);
    }
  }

  stop(): Promise<void> {
    if (this.state !== "RECORDING" || !this.recorder || this.stopPromise) {
      return this.stopPromise ?? Promise.resolve();
    }
    this.cancelled = false;
    this.clearTimer();
    this.setState("TRANSCRIBING");
    const recorder = this.recorder;
    this.stopPromise = new Promise<void>((resolve) => {
      let settled = false;
      let timeoutId: number | null = null;
      const finish = (completed: boolean) => {
        if (settled) return;
        settled = true;
        if (timeoutId !== null) (this.dependencies.clearTimeout ?? window.clearTimeout)(timeoutId);
        recorder.onstop = null;
        recorder.onerror = null;
        if (!completed) {
          this.failRecording(this.messages.recordingStopped);
          resolve();
          return;
        }
        const trackUnavailable = this.stream ? !hasUsableAudioTrack(this.stream) : true;
        const signalPresent = this.takeSignalAssessment();
        stopTracks(this.stream);
        this.stream = null;
        const captureError = trackUnavailable
          ? this.messages.microphoneUnavailable
          : signalPresent === false ? this.messages.noSpeechCaptured : null;
        void this.finishTranscription(recorder.mimeType, captureError).then(resolve, () => {
          this.failRecording(this.messages.transcriptionFailed);
          resolve();
        });
      };
      recorder.onstop = () => finish(true);
      recorder.onerror = () => finish(false);
      timeoutId = (this.dependencies.setTimeout ?? window.setTimeout)(() => finish(false), 5_000);
      if (recorder.state === "inactive") {
        finish(false);
        return;
      }
      try {
        recorder.stop();
      } catch {
        finish(false);
      }
    }).finally(() => {
      this.stopPromise = null;
    });
    return this.stopPromise;
  }

  cancel(): void {
    if (this.state !== "RECORDING" && this.state !== "REQUESTING_PERMISSION") return;
    this.cancelled = true;
    this.requestVersion += 1;
    this.clearTimer();
    this.clearSignalMonitor();
    if (this.recorder) {
      this.recorder.onstop = null;
      this.recorder.onerror = null;
      if (this.recorder.state !== "inactive") {
        try { this.recorder.stop(); } catch { /* Recorder is already stopped. */ }
      }
    }
    stopTracks(this.stream);
    this.stream = null;
    this.chunks = [];
    this.recorder = null;
    this.setState("IDLE");
  }

  dispose(): void {
    this.disposed = true;
    this.cancelled = true;
    this.requestVersion += 1;
    this.transcriptionAbort?.abort();
    this.clearTimer();
    this.clearSignalMonitor();
    if (this.recorder) {
      this.recorder.onstop = null;
      this.recorder.onerror = null;
      if (this.recorder.state !== "inactive") {
        try { this.recorder.stop(); } catch { /* Recorder is already stopped. */ }
      }
    }
    stopTracks(this.stream);
    this.stream = null;
    this.chunks = [];
    this.recorder = null;
  }

  private async finishTranscription(recorderMimeType: string, captureError: string | null): Promise<void> {
    const chunks = this.chunks;
    this.chunks = [];
    this.recorder = null;
    if (this.cancelled || this.disposed) return;
    if (captureError) {
      this.setState("IDLE");
      this.dependencies.onError(captureError);
      return;
    }
    const contentType = recorderMimeType.split(";", 1)[0] || "audio/webm";
    const audio = new Blob(chunks, { type: contentType });
    if (audio.size === 0) {
      this.setState("IDLE");
      this.dependencies.onError(this.messages.noSpeechCaptured);
      return;
    }
    const requestVersion = this.requestVersion;
    const abort = new AbortController();
    this.transcriptionAbort = abort;
    let timeoutId: number | null = null;
    try {
      const transcript = (await Promise.race([
        this.dependencies.transcribe(audio, abort.signal),
        new Promise<never>((_resolve, reject) => {
          timeoutId = (this.dependencies.setTimeout ?? window.setTimeout)(() => {
            abort.abort();
            reject(new Error("Transcription timed out."));
          }, 45_000);
        }),
      ])).trim();
      if (this.disposed || requestVersion !== this.requestVersion) return;
      if (!transcript) {
        this.dependencies.onError(this.messages.noSpeechHeard);
      } else {
        this.dependencies.onTranscript(transcript);
      }
    } catch (error) {
      if (!this.disposed && requestVersion === this.requestVersion) {
        this.dependencies.onError(error instanceof NoSpeechHeardError ? this.messages.noSpeechHeard : this.messages.transcriptionFailed);
      }
    } finally {
      if (timeoutId !== null) (this.dependencies.clearTimeout ?? window.clearTimeout)(timeoutId);
      if (this.transcriptionAbort === abort) this.transcriptionAbort = null;
      if (!this.disposed) this.setState("IDLE");
    }
  }

  private failRecording(message: string): void {
    this.cancelled = true;
    this.clearTimer();
    this.clearSignalMonitor();
    if (this.recorder) {
      this.recorder.onstop = null;
      this.recorder.onerror = null;
      if (this.recorder.state !== "inactive") {
        try { this.recorder.stop(); } catch { /* Recorder is already stopped. */ }
      }
    }
    stopTracks(this.stream);
    this.stream = null;
    this.chunks = [];
    this.recorder = null;
    if (!this.disposed) {
      this.setState("IDLE");
      this.dependencies.onError(message);
    }
  }

  private clearTimer(): void {
    if (this.timer === null) return;
    (this.dependencies.clearInterval ?? window.clearInterval)(this.timer);
    this.timer = null;
  }

  private takeSignalAssessment(): boolean | null {
    const monitor = this.signalMonitor;
    let result: boolean | null = null;
    try { result = monitor?.hasNonSilentSignal() ?? null; } catch { /* Use provider when analysis is unavailable. */ }
    this.clearSignalMonitor();
    return result;
  }

  private clearSignalMonitor(): void {
    const monitor = this.signalMonitor;
    this.signalMonitor = null;
    try { monitor?.stop(); } catch { /* Audio cleanup must not block recorder recovery. */ }
  }

  private setState(state: VoiceRecorderState): void {
    this.state = state;
    this.dependencies.onStateChange(state);
  }
}

export class NoSpeechHeardError extends Error {}

export async function transcribeDailyRecording({
  apiBaseUrl,
  learningSessionId,
  audio,
  getToken,
  signal,
  fetch: fetchRequest = fetch,
}: {
  apiBaseUrl: string;
  learningSessionId: string;
  audio: Blob;
  getToken: () => Promise<string | null>;
  signal?: AbortSignal;
  fetch?: typeof fetch;
}): Promise<{ text: string; executionId: string }> {
  const token = await getToken();
  if (signal?.aborted) throw new DOMException("Transcription cancelled.", "AbortError");
  const form = new FormData();
  form.append("audio", audio, audio.type === "audio/wav" ? "daily-recording.wav" : "daily-recording.webm");
  const response = await fetchRequest(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/student/daily/session/${learningSessionId}/voice/transcribe`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
      signal,
    },
  );
  if (!response.ok) {
    if (response.status === 422) {
      try {
        const error = await response.json() as { detail?: { code?: unknown } };
        if (error.detail?.code === "NO_SPEECH_HEARD") throw new NoSpeechHeardError();
      } catch (error) {
        if (error instanceof NoSpeechHeardError) throw error;
      }
    }
    throw new Error("The recording could not be transcribed.");
  }
  const payload = await response.json() as { transcript?: unknown; transcription_execution_id?: unknown };
  if (typeof payload.transcript !== "string" || typeof payload.transcription_execution_id !== "string") {
    throw new Error("The transcription response was invalid.");
  }
  return { text: payload.transcript, executionId: payload.transcription_execution_id };
}
