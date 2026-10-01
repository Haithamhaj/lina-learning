const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../../../..");
const { chromium } = require(path.join(root, "node_modules/playwright"));
const ts = require(path.join(root, "node_modules/typescript"));

(async () => {
  const source = fs.readFileSync(path.join(root, "apps/web/lib/daily-voice-signal.ts"), "utf8");
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 } }).outputText;
  const fixture = fs.readFileSync(path.join(root, "tests/fixtures/voice/known-speech.wav")).toString("base64");
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    await page.goto("about:blank");
    await page.addScriptTag({ content: `var exports={}; ${js}; window.probeSignal=exports.monitorMicrophoneSignal;` });
    const result = await page.evaluate(async (encoded) => {
      const bytes = Uint8Array.from(atob(encoded), (char) => char.charCodeAt(0));
      const context = new AudioContext();
      await context.resume();
      const buffer = await context.decodeAudioData(bytes.buffer.slice(0));
      const source = context.createBufferSource();
      source.buffer = buffer;
      const destination = context.createMediaStreamDestination();
      source.connect(destination);
      const speechProbe = window.probeSignal(destination.stream);
      const ended = new Promise((resolve) => { source.onended = resolve; });
      source.start();
      await ended;
      const speech = speechProbe.hasNonSilentSignal();
      speechProbe.stop();
      destination.stream.getTracks().forEach((track) => track.stop());
      await context.close();

      const silentContext = new AudioContext();
      await silentContext.resume();
      const silentDestination = silentContext.createMediaStreamDestination();
      const oscillator = silentContext.createOscillator();
      const gain = silentContext.createGain();
      gain.gain.value = 0;
      oscillator.connect(gain);
      gain.connect(silentDestination);
      const silenceProbe = window.probeSignal(silentDestination.stream);
      oscillator.start();
      await new Promise((resolve) => setTimeout(resolve, 700));
      const silence = silenceProbe.hasNonSilentSignal();
      silenceProbe.stop();
      oscillator.stop();
      silentDestination.stream.getTracks().forEach((track) => track.stop());
      await silentContext.close();
      return { speech, silence };
    }, fixture);
    assert.deepEqual(result, { speech: true, silence: false });
    console.log(JSON.stringify({ chromeSignalProbe: "pass", ...result }));
  } finally { await browser.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
