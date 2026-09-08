import assert from "node:assert/strict";
import test from "node:test";

import {
  DailyVoiceRecorder,
  formatRecordingElapsed,
  preferredRecordingMimeType,
  transcribeDailyRecording,
  voiceControlAvailability,
  type VoiceRecorderState,
} from "./daily-voice-recorder.ts";

class FakeTrack {
  stopped = false;

  stop() {
    this.stopped = true;
  }
}

class FakeStream {
  readonly track = new FakeTrack();

  getTracks() {
    return [this.track];
  }
}

class FakeMediaRecorder {
  state: RecordingState = "inactive";
  mimeType = "audio/webm;codecs=opus";
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  onstop: ((event: Event) => void) | null = null;

  start() {
    this.state = "recording";
  }

  stop() {
    if (this.state === "inactive") return;
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["voice"], { type: this.mimeType }) } as BlobEvent);
    this.onstop?.(new Event("stop"));
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

function recorderHarness(options: { permission?: Promise<FakeStream>; transcript?: Promise<string>; createFailure?: Error } = {}) {
  const stream = new FakeStream();
  const mediaRecorder = new FakeMediaRecorder();
  const states: VoiceRecorderState[] = [];
  const elapsed: number[] = [];
  const errors: string[] = [];
  const transcripts: string[] = [];
  const transcriptionBlobs: Blob[] = [];
  let intervalCallback: (() => void) | null = null;
  let clearCount = 0;
  const voice = new DailyVoiceRecorder({
    requestStream: () => options.permission ?? Promise.resolve(stream),
    createRecorder: () => {
      if (options.createFailure) throw options.createFailure;
      return mediaRecorder;
    },
    isTypeSupported: (type) => type.startsWith("audio/webm"),
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
    onStateChange: (state) => states.push(state),
    onElapsedChange: (seconds) => elapsed.push(seconds),
    onTranscript: (transcript) => transcripts.push(transcript),
    onError: (message) => errors.push(message),
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

test("an empty transcript is recoverable and does not populate the composer", async () => {
  const harness = recorderHarness({ transcript: Promise.resolve("   ") });
  await harness.voice.start();

  await harness.voice.stop();

  assert.deepEqual(harness.transcripts, []);
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
