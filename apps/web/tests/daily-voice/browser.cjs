const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, reducedMotion: "reduce" });
  page.setDefaultTimeout(5_000);
  const evidence = path.resolve(process.env.DAILY_VOICE_EVIDENCE || "output/playwright/voice-02-daily");
  fs.mkdirSync(evidence, { recursive: true });
  const screenshots = [];
  const errors = [];
  const shot = async (name) => { const file = `${name}.png`; await page.screenshot({ path: path.join(evidence, file), fullPage: true }); screenshots.push(file); };
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript(() => { window.nativeMediaRecorderForProof = window.MediaRecorder; });
  await page.goto(process.env.DAILY_VOICE_URL || "http://127.0.0.1:5086");

  const mic = page.getByRole("button", { name: "Record a message" });
  await mic.focus();
  await shot("01-idle-keyboard-focus");
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Stop recording and transcribe" }).waitFor();
  await shot("02-recording");
  assert.deepEqual(await page.evaluate(() => window.voiceProof.result()), { transcriptionRequests: 0, submittedMessages: [], stoppedTracks: 0 });

  await page.getByRole("button", { name: "Stop recording and transcribe" }).click();
  await page.getByRole("status").getByText("Transcribing your recording…").waitFor();
  await shot("03-transcribing");
  assert.equal((await page.evaluate(() => window.voiceProof.result())).transcriptionRequests, 1);
  assert.equal((await page.evaluate(() => window.voiceProof.result())).stoppedTracks, 1);
  await page.evaluate(() => window.voiceProof.completeTranscription());
  const composer = page.getByLabel("Your message for Tutor");
  await composer.waitFor({ state: "visible" });
  await page.waitForFunction(() => document.querySelector("#daily-learning-message")?.value === "What is one half?");
  await shot("04-transcript-in-composer");
  assert.deepEqual((await page.evaluate(() => window.voiceProof.result())).submittedMessages, []);
  assert.equal(await composer.isEnabled(), true);
  assert.equal(await page.getByRole("button", { name: "Send", exact: true }).isEnabled(), true);
  assert.equal(await page.locator('form button[type="button"]').first().isDisabled(), true);

  await composer.fill("What is one half as a decimal?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  assert.deepEqual((await page.evaluate(() => window.voiceProof.result())).submittedMessages, ["What is one half as a decimal?"]);

  await page.evaluate(() => window.voiceProof.failNextTranscription("http"));
  await mic.click();
  await page.getByRole("button", { name: "Stop recording and transcribe" }).click();
  await page.getByRole("alert").getByText("The recording could not be transcribed. Please try again.").waitFor();
  assert.equal(await composer.isEnabled(), true);
  assert.equal(await mic.isEnabled(), true);
  await shot("05-provider-failure-recovers");

  await page.evaluate(() => window.voiceProof.failNextTranscription("no-speech"));
  await mic.click();
  await page.getByRole("button", { name: "Stop recording and transcribe" }).click();
  await page.getByRole("alert").getByText("I couldn't hear clear speech. Check your microphone and try again.").waitFor();
  assert.match(await page.getByRole("alert").getAttribute("class"), /bg-rose-50/);
  assert.equal(await composer.isEnabled(), true);
  await shot("06-no-speech-alert");
  await composer.fill("I will type instead.");
  assert.equal(await page.getByRole("button", { name: "Send", exact: true }).isEnabled(), true);
  await page.getByRole("button", { name: "Send", exact: true }).click();
  assert.deepEqual((await page.evaluate(() => window.voiceProof.result())).submittedMessages, ["What is one half as a decimal?", "I will type instead."]);

  await mic.click();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  assert.equal((await page.evaluate(() => window.voiceProof.result())).transcriptionRequests, 3);
  assert.equal((await page.evaluate(() => window.voiceProof.result())).stoppedTracks, 4);

  await page.evaluate(() => window.voiceProof.silentMicNext());
  await mic.click();
  await page.getByRole("button", { name: "Stop recording and transcribe" }).waitFor();
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Stop recording and transcribe" }).click();
  await page.getByRole("alert").getByText("The microphone did not capture clear sound. Check it and try again.").waitFor();
  assert.equal((await page.evaluate(() => window.voiceProof.result())).transcriptionRequests, 3);
  assert.equal(await composer.isEnabled(), true);
  assert.equal(await mic.isEnabled(), true);
  await shot("07-silent-microphone-recovers");
  await page.evaluate(() => window.voiceProof.closeSilentMic());

  await page.setViewportSize({ width: 320, height: 800 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await shot("06-narrow-after-cancel");

  const knownSpeech = fs.readFileSync(path.resolve(__dirname, "../../../../tests/fixtures/voice/known-speech.wav"));
  const recorded = await page.evaluate(async (encoded) => {
    const wav = Uint8Array.from(atob(encoded), (char) => char.charCodeAt(0));
    const context = new AudioContext();
    await context.resume();
    const decoded = await context.decodeAudioData(wav.buffer.slice(0));
    const source = context.createBufferSource();
    source.buffer = decoded;
    const destination = context.createMediaStreamDestination();
    source.connect(destination);
    const NativeRecorder = window.nativeMediaRecorderForProof;
    const mimeType = NativeRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
    const recorder = new NativeRecorder(destination.stream, { mimeType, audioBitsPerSecond: 32_000 });
    const chunks = [];
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    const stopped = new Promise((resolve) => { recorder.onstop = resolve; });
    recorder.start();
    const played = new Promise((resolve) => { source.onended = resolve; });
    source.start();
    await played;
    await new Promise((resolve) => setTimeout(resolve, 250));
    recorder.stop();
    await stopped;
    destination.stream.getTracks().forEach((track) => track.stop());
    await context.close();
    const bytes = await new Blob(chunks, { type: "audio/webm" }).arrayBuffer();
    return { mimeType, durationSeconds: decoded.duration, bytes: Array.from(new Uint8Array(bytes)) };
  }, knownSpeech.toString("base64"));
  const webmPath = path.join(evidence, "chrome-media-recorder.webm");
  fs.writeFileSync(webmPath, Buffer.from(recorded.bytes));
  const mediaProbe = execFileSync("ffprobe", ["-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", webmPath], { encoding: "utf8" }).trim();
  assert.equal(mediaProbe, "opus");
  const mediaDuration = Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", webmPath], { encoding: "utf8" }).trim());
  assert.ok(mediaDuration > 1.8);
  await browser.close();

  const payload = { environment: "Chrome with deterministic getUserMedia and recorder boundary; native Chrome MediaRecorder known-speech probe", productionComponent: "DailyVoiceInput used by DailyStudentApp", physicalMicrophone: false, screenshots, result: { transcriptionRequests: 3, submittedMessages: 2, cancelledRequests: 0, nativeRecording: { mimeType: recorded.mimeType, durationSeconds: recorded.durationSeconds, bytes: recorded.bytes.length, codec: mediaProbe } }, errors };
  fs.writeFileSync(path.join(evidence, "results.json"), `${JSON.stringify(payload, null, 2)}\n`);
  assert.deepEqual(errors, []);
})().catch((error) => { console.error(error); process.exitCode = 1; });
