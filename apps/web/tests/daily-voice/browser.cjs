const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
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
  await page.goto(process.env.DAILY_VOICE_URL || "http://127.0.0.1:5086");

  const mic = page.getByRole("button", { name: "Record a message" });
  await mic.focus();
  await shot("01-idle-keyboard-focus");
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Stop recording and transcribe" }).waitFor();
  await shot("02-recording");
  assert.deepEqual(await page.evaluate(() => window.voiceProof.result()), { transcriptionRequests: 0, submittedMessages: [], stoppedTracks: 0 });

  await page.getByRole("button", { name: "Stop recording and transcribe" }).click();
  await page.getByText("Transcribing your recording…").waitFor();
  await shot("03-transcribing");
  assert.equal((await page.evaluate(() => window.voiceProof.result())).transcriptionRequests, 1);
  assert.equal((await page.evaluate(() => window.voiceProof.result())).stoppedTracks, 1);
  await page.evaluate(() => window.voiceProof.completeTranscription());
  const composer = page.getByLabel("Your message for Tutor");
  await composer.waitFor({ state: "visible" });
  await page.waitForFunction(() => document.querySelector("#daily-learning-message")?.value === "What is one half?");
  await shot("04-transcript-in-composer");
  assert.deepEqual((await page.evaluate(() => window.voiceProof.result())).submittedMessages, []);
  assert.equal(await page.locator('form button[type="button"]').first().isDisabled(), true);

  await composer.fill("What is one half as a decimal?");
  await page.getByRole("button", { name: "Send" }).click();
  assert.deepEqual((await page.evaluate(() => window.voiceProof.result())).submittedMessages, ["What is one half as a decimal?"]);

  await mic.click();
  await page.getByRole("button", { name: "Cancel recording" }).click();
  assert.equal((await page.evaluate(() => window.voiceProof.result())).transcriptionRequests, 1);
  assert.equal((await page.evaluate(() => window.voiceProof.result())).stoppedTracks, 2);

  await page.setViewportSize({ width: 320, height: 800 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await shot("05-narrow-after-cancel");
  await browser.close();

  const payload = { environment: "Chrome with deterministic getUserMedia and MediaRecorder boundary", productionComponent: "DailyVoiceInput used by DailyStudentApp", physicalMicrophone: false, screenshots, result: { transcriptionRequests: 1, submittedMessages: 1, cancelledRequests: 0 }, errors };
  fs.writeFileSync(path.join(evidence, "results.json"), `${JSON.stringify(payload, null, 2)}\n`);
  assert.deepEqual(errors, []);
})().catch((error) => { console.error(error); process.exitCode = 1; });
