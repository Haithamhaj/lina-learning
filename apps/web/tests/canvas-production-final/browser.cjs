const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, reducedMotion: "reduce" });
  const evidence = path.resolve(process.env.CANVAS_PRODUCTION_EVIDENCE || "output/playwright/canvas-production-final");
  fs.mkdirSync(evidence, { recursive: true });
  const errors = [], badAssets = [], results = [], screenshots = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("response", response => { if (response.status() >= 400) badAssets.push({ status: response.status(), url: response.url() }); });
  const shot = async name => { const file = `${name}.png`; await page.screenshot({ path: path.join(evidence, file), fullPage: true }); screenshots.push(file); };
  const check = async (name, fn) => { try { await fn(); results.push({ name, pass: true }); } catch (error) { results.push({ name, pass: false, error: error.message }); } };
  await page.goto(process.env.CANVAS_PRODUCTION_URL || "http://127.0.0.1:5082");
  await page.waitForSelector('[data-pattern="PROCESS"]');

  await shot("process-initial");
  await check("PROCESS focus, reload, and Tutor continuation", async () => {
    const stage = page.locator("[data-stage]").nth(1); await stage.focus(); await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "اشرح هذه المرحلة" }).click();
    await page.getByText("أعد التحميل من Snapshot").click();
    assert.match(await page.locator("[data-operation]").innerText(), /REQUEST_EXPLANATION/);
    assert.match(await page.locator("[data-tutor]").innerText(), /نفس جلسة/);
  });
  await shot("process-completed");

  await page.getByRole("button", { name: "المكان", exact: true }).click(); await page.waitForFunction(() => window.canvasEngineCounts?.().stages === 1);
  await shot("spatial-initial");
  await check("SPATIAL semantic placement survives Renderer Host reload", async () => {
    await page.getByRole("button", { name: /Place .* in .*/ }).click();
    assert.match(await page.locator("[data-operation]").innerText(), /PLACE_OBJECT/);
    assert.doesNotMatch(await page.locator("[data-operation]").innerText(), /\b[xy]\b/);
    await page.getByText("أعد التحميل من Snapshot").click();
    assert.match(await page.locator(".toolbelt-card output").innerText(), /داخل/);
  });
  await shot("spatial-placed-reloaded");

  await page.getByRole("button", { name: "الإحداثيات", exact: true }).click(); await page.waitForFunction(() => window.canvasEngineCounts?.().boards === 1);
  await shot("math-visualization-initial");
  await check("MATH_VISUALIZATION saves exact point, reloads, and explicitly submits", async () => {
    const xInput = page.getByRole("spinbutton", { name: "X coordinate" });
    const yInput = page.getByRole("spinbutton", { name: "Y coordinate" });
    assert.equal(await xInput.getAttribute("min"), "-10");
    assert.equal(await xInput.getAttribute("max"), "10");
    assert.equal(await yInput.getAttribute("min"), "-10");
    assert.equal(await yInput.getAttribute("max"), "10");
    assert.deepEqual(await page.evaluate(() => window.canvasCoordinateBounds?.()), [-11, 11, 11, -11]);
    await xInput.fill("-10");
    await yInput.fill("10");
    await page.getByRole("button", { name: "احفظ موضع النقطة" }).click();
    await page.getByText("أعد التحميل من Snapshot").click();
    assert.equal(await page.locator(".toolbelt-card output").innerText(), "A = (-10, 10)");
    await page.getByRole("button", { name: "أرسل البناء إلى المعلّم" }).click();
    assert.match(await page.locator("[data-tutor]").innerText(), /SUBMIT_CONSTRUCTION/);
  });
  await shot("math-visualization-submitted");

  await page.getByRole("button", { name: "التعبير", exact: true }).click(); await page.waitForSelector("math-field");
  await shot("math-input-initial");
  await check("MATH_INPUT keeps edits local until explicit submit and reloads submitted LaTeX", async () => {
    const field = page.locator("math-field"); await field.click();
    await field.evaluate(node => { node.value = "\\frac{3}{4}+\\frac{1}{4}"; node.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" })); });
    await page.waitForFunction(() => document.querySelector("math-field")?.value.includes("frac"));
    assert.match(await page.locator("[data-operation]").innerText(), /لم يُسجل/);
    await page.getByRole("button", { name: "Submit expression" }).click();
    assert.match(await page.locator("[data-operation]").innerText(), /SUBMIT_EXPRESSION/);
    await page.getByText("أعد التحميل من Snapshot").click();
    assert.notEqual(await page.locator("math-field").evaluate(node => node.value), "");
  });
  await shot("math-input-submitted-reloaded");

  await check("narrow and wide layouts have no page overflow", async () => {
    for (const width of [320, 1280]) { await page.setViewportSize({ width, height: 900 }); await page.waitForTimeout(100); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); }
  });
  await page.setViewportSize({ width: 1280, height: 900 }); await shot("daily-host-wide");
  await browser.close();
  const payload = { environment: "Authenticated-independent Chrome harness using exact production Scene contracts and StudioRendererHost; Clerk configuration absent", host: "StudioRendererHost used by /student/daily", reducedMotion: true, results, screenshots, errors, badAssets };
  fs.writeFileSync(path.join(evidence, "results.json"), JSON.stringify(payload, null, 2) + "\n");
  assert.equal(results.filter(result => !result.pass).length, 0, JSON.stringify(results));
  assert.deepEqual(errors, []); assert.deepEqual(badAssets, []);
})().catch(error => { console.error(error); process.exitCode = 1; });
