export type VoiceRecorderState = "IDLE" | "REQUESTING_PERMISSION" | "RECORDING" | "TRANSCRIBING";

type TrackLike = { stop: () => void };
type StreamLike = { getTracks: () => TrackLike[] };
type RecorderLike = {
  state: RecordingState;
  mimeType: string;
  ondataavailable: ((event: BlobEvent) => void) | null;
  onerror: ((event: ErrorEvent) => void) | null;
  onstop: ((event: Event) => void) | null;
  start: () => void;
  stop: () => void;
};

type VoiceRecorderDependencies = {
  requestStream: () => Promise<StreamLike>;
  createRecorder: (stream: StreamLike, mimeType: string) => RecorderLike;
  isTypeSupported?: (mimeType: string) => boolean;
  transcribe: (audio: Blob) => Promise<string>;
  now?: () => number;
  setInterval?: (callback: () => void, milliseconds: number) => number;
  clearInterval?: (id: number) => void;
  onStateChange: (state: VoiceRecorderState) => void;
  onElapsedChange: (seconds: number) => void;
  onTranscript: (transcript: string) => void;
  onError: (message: string) => void;
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
}: {
  state: VoiceRecorderState;
  draft: string;
  chatSending: boolean;
}): { canStart: boolean; reason: string } {
  if (draft.trim()) return { canStart: false, reason: "Send or clear your typed message before recording." };
  if (chatSending) return { canStart: false, reason: "Wait for Tutor before recording." };
  if (state !== "IDLE") return { canStart: false, reason: "Voice input is already active." };
  return { canStart: true, reason: "Record a message" };
}

function stopTracks(stream: StreamLike | null) {
  stream?.getTracks().forEach((track) => track.stop());
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
      const mimeType = preferredRecordingMimeType(
        this.dependencies.isTypeSupported ?? ((type) => MediaRecorder.isTypeSupported(type)),
      );
      if (!mimeType) {
        stopTracks(stream);
        this.setState("IDLE");
        this.dependencies.onError("Voice recording is not supported in this browser.");
        return;
      }
      this.stream = stream;
      this.cancelled = false;
      this.chunks = [];
      const recorder = this.dependencies.createRecorder(stream, mimeType);
      this.recorder = recorder;
      recorder.ondataavailable = (event) => {
        if (!this.cancelled && event.data.size > 0) this.chunks.push(event.data);
      };
      recorder.onerror = () => this.failRecording("Voice recording stopped unexpectedly. Please try again.");
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
      stopTracks(this.stream);
      this.stream = null;
      this.recorder = null;
      this.chunks = [];
      this.setState("IDLE");
      const denied = error instanceof DOMException && error.name === "NotAllowedError";
      this.dependencies.onError(denied
        ? "Microphone permission was denied. You can keep typing or allow microphone access and try again."
        : "The microphone could not be opened. You can keep typing and try again.");
    }
  }

  stop(): Promise<void> {
    if (this.state !== "RECORDING" || !this.recorder || this.stopPromise) {
      return this.stopPromise ?? Promise.resolve();
    }
    this.cancelled = false;
    this.clearTimer();
    stopTracks(this.stream);
    this.stream = null;
    this.setState("TRANSCRIBING");
    const recorder = this.recorder;
    this.stopPromise = new Promise<void>((resolve) => {
      recorder.onstop = () => {
        void this.finishTranscription(recorder.mimeType).finally(resolve);
      };
      recorder.stop();
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
    stopTracks(this.stream);
    this.stream = null;
    this.chunks = [];
    if (this.recorder && this.recorder.state !== "inactive") this.recorder.stop();
    this.recorder = null;
    this.setState("IDLE");
  }

  dispose(): void {
    this.disposed = true;
    this.cancelled = true;
    this.requestVersion += 1;
    this.clearTimer();
    stopTracks(this.stream);
    this.stream = null;
    this.chunks = [];
    if (this.recorder && this.recorder.state !== "inactive") this.recorder.stop();
    this.recorder = null;
  }

  private async finishTranscription(recorderMimeType: string): Promise<void> {
    const chunks = this.chunks;
    this.chunks = [];
    this.recorder = null;
    if (this.cancelled || this.disposed) return;
    const contentType = recorderMimeType.split(";", 1)[0] || "audio/webm";
    const audio = new Blob(chunks, { type: contentType });
    if (audio.size === 0) {
      this.setState("IDLE");
      this.dependencies.onError("No speech was captured. Please record again.");
      return;
    }
    try {
      const transcript = (await this.dependencies.transcribe(audio)).trim();
      if (!transcript) {
        this.dependencies.onError("We could not hear any speech. Please record again.");
      } else {
        this.dependencies.onTranscript(transcript);
      }
    } catch {
      this.dependencies.onError("The recording could not be transcribed. Please try again.");
    } finally {
      if (!this.disposed) this.setState("IDLE");
    }
  }

  private failRecording(message: string): void {
    this.cancelled = true;
    this.clearTimer();
    stopTracks(this.stream);
    this.stream = null;
    this.chunks = [];
    if (this.recorder && this.recorder.state !== "inactive") this.recorder.stop();
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

  private setState(state: VoiceRecorderState): void {
    this.state = state;
    this.dependencies.onStateChange(state);
  }
}

export async function transcribeDailyRecording({
  apiBaseUrl,
  learningSessionId,
  audio,
  getToken,
  fetch: fetchRequest = fetch,
}: {
  apiBaseUrl: string;
  learningSessionId: string;
  audio: Blob;
  getToken: () => Promise<string | null>;
  fetch?: typeof fetch;
}): Promise<{ text: string; executionId: string }> {
  const token = await getToken();
  const form = new FormData();
  form.append("audio", audio, audio.type === "audio/wav" ? "daily-recording.wav" : "daily-recording.webm");
  const response = await fetchRequest(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/student/daily/session/${learningSessionId}/voice/transcribe`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    },
  );
  if (!response.ok) throw new Error("The recording could not be transcribed.");
  const payload = await response.json() as { transcript?: unknown; transcription_execution_id?: unknown };
  if (typeof payload.transcript !== "string" || typeof payload.transcription_execution_id !== "string") {
    throw new Error("The transcription response was invalid.");
  }
  return { text: payload.transcript, executionId: payload.transcription_execution_id };
}
