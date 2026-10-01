import assert from "node:assert/strict";
import test from "node:test";

import {
  DailyVoiceRecorder,
  NoSpeechHeardError,
  formatRecordingElapsed,
  preferredRecordingMimeType,
  transcribeDailyRecording,
  voiceControlAvailability,
  type VoiceRecorderMessages,
  type VoiceRecorderState,
} from "./daily-voice-recorder.ts";

class FakeTrack {
  stopped = false;
  onStop: (() => void) | null = null;
  readyState: MediaStreamTrackState = "live";
  enabled = true;
  muted = false;

  stop() {
    this.stopped = true;
    this.onStop?.();
  }
}

class FakeStream {
  readonly track = new FakeTrack();

  getTracks() {
    return [this.track];
  }

  getAudioTracks() {
    return [this.track];
  }
}

class FakeMediaRecorder {
  state: RecordingState = "inactive";
  mimeType = "audio/webm;codecs=opus";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  onstop: ((event: Event) => void) | null = null;
  suppressStopEvent = false;
  throwOnStop = false;
  omitData = false;

  start() {
    this.state = "recording";
  }

  stop() {
    if (this.throwOnStop) throw new DOMException("Recorder already inactive", "InvalidStateError");
    if (this.state === "inactive") return;
    this.state = "inactive";
    if (!this.omitData) this.ondataavailable?.({ data: new Blob(["voice"], { type: this.mimeType }) } as BlobEvent);
    if (!this.suppressStopEvent) this.onstop?.(new Event("stop"));
  }

  fail() {
    this.onerror?.(new Event("error") as ErrorEvent);
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function recorderHarness(options: { permission?: Promise<FakeStream>; transcript?: Promise<string>; createFailure?: Error; supported?: boolean; messages?: VoiceRecorderMessages; signal?: boolean | null } = {}) {
  const stream = new FakeStream();
  const mediaRecorder = new FakeMediaRecorder();
  const states: VoiceRecorderState[] = [];
  const elapsed: number[] = [];
  const errors: string[] = [];
  const transcripts: string[] = [];
  const transcriptionBlobs: Blob[] = [];
  let intervalCallback: (() => void) | null = null;
  let clearCount = 0;
  let nextTimeoutId = 100;
  const timeouts = new Map<number, () => void>();
  const voice = new DailyVoiceRecorder({
    requestStream: () => options.permission ?? Promise.resolve(stream),
    createRecorder: () => {
      if (options.createFailure) throw options.createFailure;
      return mediaRecorder;
    },
    isTypeSupported: (type) => options.supported !== false && type.startsWith("audio/webm"),
    createSignalMonitor: () => ({ hasNonSilentSignal: () => options.signal ?? null, stop: () => {} }),
    transcribe: async (blob) => {
      transcriptionBlobs.push(blob);
      return options.transcript ?? Promise.resolve("One half equals 0.5.");
    },
    now: (() => {
      let value = 0;
      return () => value += 1_000;
    })(),
    setInterval: (callback) => {
      intervalCallback = callback;
      return 41;
    },
    clearInterval: (id) => {
      assert.equal(id, 41);
      clearCount += 1;
      intervalCallback = null;
    },
    setTimeout: (callback) => {
      const id = nextTimeoutId++;
      timeouts.set(id, callback);
      return id;
    },
    clearTimeout: (id) => { timeouts.delete(id); },
    onStateChange: (state) => states.push(state),
    onElapsedChange: (seconds) => elapsed.push(seconds),
    onTranscript: (transcript) => transcripts.push(transcript),
    onError: (message) => errors.push(message),
    messages: options.messages,
  });
  return {
    voice,
    stream,
    mediaRecorder,
    states,
    elapsed,
    errors,
    transcripts,
    transcriptionBlobs,
    tick: () => intervalCallback?.(),
    clearCount: () => clearCount,
    fireTimeouts: () => {
      const callbacks = Array.from(timeouts.values());
      timeouts.clear();
      callbacks.forEach((callback) => callback());
    },
  };
}

test("an explicit start requests permission and enters recording with an informational timer", async () => {
  const permission = deferred<FakeStream>();
  const harness = recorderHarness({ permission: permission.promise });

  const starting = harness.voice.start();
  assert.deepEqual(harness.states, ["REQUESTING_PERMISSION"]);
  permission.resolve(harness.stream);
  await starting;
  harness.tick();

  assert.deepEqual(harness.states, ["REQUESTING_PERMISSION", "RECORDING"]);
  assert.equal(harness.elapsed.at(-1), 1);
  assert.equal(harness.mediaRecorder.state, "recording");
});

test("recording has no time-based stop and only Stop creates one transcription", async () => {
  const harness = recorderHarness();
  await harness.voice.start();

  for (let minute = 0; minute < 90; minute += 1) harness.tick();
  assert.equal(harness.mediaRecorder.state, "recording");
  assert.equal(harness.transcriptionBlobs.length, 0);

  await harness.voice.stop();
  await harness.voice.stop();

  assert.deepEqual(harness.states, ["REQUESTING_PERMISSION", "RECORDING", "TRANSCRIBING", "IDLE"]);
  assert.equal(harness.transcriptionBlobs.length, 1);
  assert.deepEqual(harness.transcripts, ["One half equals 0.5."]);
  assert.equal(harness.stream.track.stopped, true);
  assert.equal(harness.clearCount(), 1);
});

test("a live but silent microphone skips provider transcription and remains reusable", async () => {
  const harness = recorderHarness({ signal: false });
  await harness.voice.start();
  await harness.voice.stop();

  assert.equal(harness.transcriptionBlobs.length, 0);
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /microphone|speech|sound/i);

  await harness.voice.start();
  assert.equal(harness.states.at(-1), "RECORDING");
  harness.voice.cancel();
});

test("a missing, disabled, or muted audio track is rejected before recording", async () => {
  for (const condition of ["missing", "disabled", "muted", "ended"] as const) {
    const harness = recorderHarness();
    if (condition === "missing") harness.stream.getAudioTracks = () => [];
    if (condition === "disabled") harness.stream.track.enabled = false;
    if (condition === "muted") harness.stream.track.muted = true;
    if (condition === "ended") harness.stream.track.readyState = "ended";
    await harness.voice.start();

    assert.equal(harness.stream.track.stopped, true);
    assert.equal(harness.mediaRecorder.state, "inactive");
    assert.equal(harness.states.at(-1), "IDLE");
    assert.match(harness.errors.at(-1) ?? "", /microphone/i);
  }
});

test("the recorder can complete two stop/transcribe cycles without auto-sending", async () => {
  const harness = recorderHarness({ signal: true });
  await harness.voice.start();
  await harness.voice.stop();
  await harness.voice.start();
  await harness.voice.stop();

  assert.equal(harness.transcriptionBlobs.length, 2);
  assert.equal(harness.transcripts.length, 2);
  assert.equal(harness.states.at(-1), "IDLE");
});

test("Cancel discards audio, preserves the draft owner, and creates no transcription", async () => {
  const harness = recorderHarness();
  await harness.voice.start();

  harness.voice.cancel();

  assert.equal(harness.transcriptionBlobs.length, 0);
  assert.equal(harness.stream.track.stopped, true);
  assert.equal(harness.states.at(-1), "IDLE");
});

test("permission denial is recoverable and creates no transcription", async () => {
  const harness = recorderHarness({ permission: Promise.reject(new DOMException("Denied", "NotAllowedError")) });

  await harness.voice.start();

  assert.equal(harness.transcriptionBlobs.length, 0);
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /permission/i);
});

test("recorder failures use caller-owned localized copy", async () => {
  const harness = recorderHarness({
    permission: Promise.reject(new DOMException("Denied", "NotAllowedError")),
    messages: {
      unsupported: "غير مدعوم",
      recordingStopped: "توقف التسجيل",
      permissionDenied: "رُفض إذن الميكروفون.",
      openFailed: "تعذر فتح الميكروفون.",
      microphoneUnavailable: "الميكروفون لا يرسل صوتًا.",
      noSpeechCaptured: "لم يُلتقط صوت.",
      noSpeechHeard: "لم نسمع كلامًا.",
      transcriptionFailed: "تعذر تحويل التسجيل.",
    },
  });

  await harness.voice.start();

  assert.equal(harness.errors.at(-1), "رُفض إذن الميكروفون.");
});

test("dispose during permission request stops a late stream and never records", async () => {
  const permission = deferred<FakeStream>();
  const harness = recorderHarness({ permission: permission.promise });

  const starting = harness.voice.start();
  harness.voice.dispose();
  permission.resolve(harness.stream);
  await starting;

  assert.equal(harness.stream.track.stopped, true);
  assert.equal(harness.mediaRecorder.state, "inactive");
  assert.equal(harness.transcriptionBlobs.length, 0);
});

test("recorder failure releases the microphone and creates no transcription", async () => {
  const harness = recorderHarness();
  await harness.voice.start();

  harness.mediaRecorder.fail();

  assert.equal(harness.stream.track.stopped, true);
  assert.equal(harness.transcriptionBlobs.length, 0);
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /record/i);
});

test("device initialization failure releases a granted microphone stream", async () => {
  const harness = recorderHarness({ createFailure: new Error("device unavailable") });

  await harness.voice.start();

  assert.equal(harness.stream.track.stopped, true);
  assert.equal(harness.transcriptionBlobs.length, 0);
  assert.equal(harness.states.at(-1), "IDLE");
});

test("unsupported recording type releases the stream and returns to idle", async () => {
  const harness = recorderHarness({ supported: false });
  await harness.voice.start();
  assert.equal(harness.stream.track.stopped, true);
  assert.equal(harness.mediaRecorder.state, "inactive");
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /not supported/i);
});

test("an empty transcript is recoverable and does not populate the composer", async () => {
  const harness = recorderHarness({ transcript: Promise.resolve("   ") });
  await harness.voice.start();

  await harness.voice.stop();

  assert.deepEqual(harness.transcripts, []);
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /hear|speech/i);
});

test("an empty completed recording reports no speech captured without sending audio", async () => {
  const harness = recorderHarness();
  await harness.voice.start();
  harness.mediaRecorder.omitData = true;
  await harness.voice.stop();

  assert.deepEqual(harness.transcriptionBlobs, []);
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /captured/i);
});

test("a provider no-speech response uses the distinct recoverable message", async () => {
  const harness = recorderHarness({ transcript: Promise.reject(new NoSpeechHeardError()) });
  await harness.voice.start();
  await harness.voice.stop();

  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /hear|speech/i);
});

test("STT failure is recoverable and never produces a transcript", async () => {
  const harness = recorderHarness({ transcript: Promise.reject(new Error("offline")) });
  await harness.voice.start();

  await harness.voice.stop();

  assert.deepEqual(harness.transcripts, []);
  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /transcrib/i);
});

test("Stop installs its completion handler before tracks can terminate the recorder", async () => {
  const harness = recorderHarness();
  harness.stream.track.onStop = () => {
    if (harness.mediaRecorder.state === "recording") harness.mediaRecorder.stop();
  };
  await harness.voice.start();

  await harness.voice.stop();

  assert.deepEqual(harness.transcripts, ["One half equals 0.5."]);
  assert.equal(harness.states.at(-1), "IDLE");
});

test("an already inactive recorder and a throwing Stop both recover", async () => {
  for (const mode of ["inactive", "throw"] as const) {
    const harness = recorderHarness();
    await harness.voice.start();
    if (mode === "inactive") harness.mediaRecorder.state = "inactive";
    else harness.mediaRecorder.throwOnStop = true;

    await harness.voice.stop();

    assert.equal(harness.states.at(-1), "IDLE");
    assert.equal(harness.stream.track.stopped, true);
    assert.equal(harness.transcriptionBlobs.length, 0);
    assert.match(harness.errors.at(-1) ?? "", /stopped/i);
  }
});

test("a missing stop event cannot strand the voice state", async () => {
  const harness = recorderHarness();
  await harness.voice.start();
  harness.mediaRecorder.suppressStopEvent = true;
  const stopping = harness.voice.stop();

  harness.fireTimeouts();
  await stopping;

  assert.equal(harness.states.at(-1), "IDLE");
  assert.equal(harness.stream.track.stopped, true);
  assert.match(harness.errors.at(-1) ?? "", /stopped/i);
});

test("transcription timeout recovers and ignores a late transcript", async () => {
  const transcript = deferred<string>();
  const harness = recorderHarness({ transcript: transcript.promise });
  await harness.voice.start();
  const stopping = harness.voice.stop();
  harness.fireTimeouts();
  await stopping;

  assert.equal(harness.states.at(-1), "IDLE");
  assert.match(harness.errors.at(-1) ?? "", /transcrib/i);
  transcript.resolve("late speech");
  await Promise.resolve();
  assert.deepEqual(harness.transcripts, []);
});

test("disposing during transcription ignores its late result", async () => {
  const transcript = deferred<string>();
  const harness = recorderHarness({ transcript: transcript.promise });
  await harness.voice.start();
  const stopping = harness.voice.stop();
  harness.voice.dispose();
  transcript.resolve("late speech");
  await stopping;
  assert.deepEqual(harness.transcripts, []);
});

test("webm opus is preferred and unsupported browsers are explicit", () => {
  assert.equal(preferredRecordingMimeType((type) => type === "audio/webm;codecs=opus"), "audio/webm;codecs=opus");
  assert.equal(preferredRecordingMimeType((type) => type === "audio/webm"), "audio/webm");
  assert.equal(preferredRecordingMimeType(() => false), null);
});

test("the visible timer keeps counting beyond one hour without becoming a duration limit", () => {
  assert.equal(formatRecordingElapsed(0), "00:00");
  assert.equal(formatRecordingElapsed(61), "01:01");
  assert.equal(formatRecordingElapsed(3_661), "1:01:01");
});

test("microphone start is unavailable while the existing composer owns non-empty text", () => {
  assert.deepEqual(voiceControlAvailability({ state: "IDLE", draft: "typed answer", chatSending: false }), {
    canStart: false,
    reason: "Send or clear your typed message before recording.",
  });
  assert.deepEqual(voiceControlAvailability({ state: "IDLE", draft: "", chatSending: false }), {
    canStart: true,
    reason: "Record a message",
  });
  assert.equal(voiceControlAvailability({ state: "TRANSCRIBING", draft: "", chatSending: false }).canStart, false);
});

test("the transcription client sends exactly one authenticated multipart audio request", async () => {
  const requests: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const transcript = await transcribeDailyRecording({
    apiBaseUrl: "https://api.example.test/",
    learningSessionId: "session-123",
    audio: new Blob(["voice"], { type: "audio/webm;codecs=opus" }),
    getToken: async () => "student-token",
    fetch: async (input, init) => {
      requests.push({ input, init });
      return new Response(JSON.stringify({
        transcript: "What is one half?",
        transcription_execution_id: "execution-123",
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    },
  });

  assert.deepEqual(transcript, { text: "What is one half?", executionId: "execution-123" });
  assert.equal(requests.length, 1);
  assert.equal(requests[0]?.input, "https://api.example.test/v1/student/daily/session/session-123/voice/transcribe");
  assert.equal(requests[0]?.init?.method, "POST");
  assert.deepEqual(requests[0]?.init?.headers, { Authorization: "Bearer student-token" });
  const body = requests[0]?.init?.body;
  assert.ok(body instanceof FormData);
  assert.ok(body.get("audio") instanceof Blob);
});

test("the transcription client distinguishes no speech from provider and malformed failures", async () => {
  const base = {
    apiBaseUrl: "https://api.example.test",
    learningSessionId: "session-123",
    audio: new Blob(["voice"], { type: "audio/webm" }),
    getToken: async () => "student-token",
  };
  await assert.rejects(
    transcribeDailyRecording({ ...base, fetch: async () => new Response(JSON.stringify({ detail: { code: "NO_SPEECH_HEARD" } }), { status: 422 }) }),
    NoSpeechHeardError,
  );
  await assert.rejects(
    transcribeDailyRecording({ ...base, fetch: async () => new Response("provider unavailable", { status: 502 }) }),
    /could not be transcribed/i,
  );
  await assert.rejects(
    transcribeDailyRecording({ ...base, fetch: async () => { throw new TypeError("offline"); } }),
    /offline/,
  );
  await assert.rejects(
    transcribeDailyRecording({ ...base, fetch: async () => new Response("not json", { status: 200 }) }),
    /json/i,
  );
});

test("an aborted transcription does not send audio after delayed token retrieval", async () => {
  const token = deferred<string | null>();
  const abort = new AbortController();
  let fetches = 0;
  const attempt = transcribeDailyRecording({
    apiBaseUrl: "https://api.example.test",
    learningSessionId: "session-123",
    audio: new Blob(["voice"], { type: "audio/webm" }),
    getToken: () => token.promise,
    signal: abort.signal,
    fetch: async () => { fetches += 1; throw new Error("fetch must not happen"); },
  });
  abort.abort();
  token.resolve("student-token");
  await assert.rejects(attempt, { name: "AbortError" });
  assert.equal(fetches, 0);
});
