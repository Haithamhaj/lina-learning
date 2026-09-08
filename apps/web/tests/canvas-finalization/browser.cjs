const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const results = [];
  const errors = [];
  const badAssets = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => { if (response.status() >= 400) badAssets.push(response.url()); });
  const url = process.env.CANVAS_FINAL_URL || "http://127.0.0.1:5078";
  const evidence = path.resolve(process.env.CANVAS_FINAL_EVIDENCE || "/tmp/lina-canvas-final-evidence");
  fs.mkdirSync(evidence, { recursive: true });
  const check = async (name, fn) => {
    try { await fn(); results.push({ name, pass: true }); console.log("PASS", name); }
    catch (error) { results.push({ name, pass: false, error: error.message }); console.log("FAIL", name, error.message); }
  };

  await page.goto(url);
  await page.waitForFunction(() => window.canvasEngineCounts?.().stages === 1 && window.canvasEngineCounts?.().boards === 1 && document.querySelector("math-field"));

  await check("review exposes four finalized patterns and both Process topologies", async () => {
    assert.equal(await page.locator('[data-canvas-pattern="PROCESS"]').count(), 2);
    assert.equal(await page.locator('[data-canvas-pattern="SPATIAL_MANIPULATION"]').count(), 1);
    assert.equal(await page.locator('[data-canvas-pattern="MATH_VISUALIZATION"]').count(), 1);
    assert.equal(await page.locator('[data-canvas-pattern="MATH_INPUT"]').count(), 1);
    assert.equal(await page.locator('[data-process-topology="sequence"]').count(), 1);
    assert.equal(await page.locator('[data-process-topology="cycle"]').count(), 1);
  });

  await check("selection surface records semantic inputs and application pattern results", async () => {
    const selections = await page.locator("[data-selection-input]").evaluateAll((nodes) => nodes.map((node) => ({
      input: JSON.parse(node.getAttribute("data-selection-input")),
      result: node.getAttribute("data-selection-result"),
      adapter: node.getAttribute("data-selection-adapter"),
    })));
    assert.deepEqual(selections.map((item) => item.result), ["PROCESS", "PROCESS", "SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT"]);
    assert.deepEqual(selections.map((item) => item.input.type), ["explain_process", "explain_process", "place_object", "construct_coordinate", "author_math"]);
    assert.deepEqual(selections.map((item) => item.adapter), ["process-view", "process-view", "spatial-placement", "coordinate-construction", "math-expression-input"]);
  });

  for (const topology of ["sequence", "cycle"]) await check(`Process ${topology} accepts a student focus and returns semantic state`, async () => {
    const article = page.locator(`[data-process-topology="${topology}"]`);
    const stage = article.locator("[data-stage]").nth(1);
    await stage.focus();
    await page.keyboard.press("Enter");
    const result = JSON.parse(await article.locator("[data-semantic-result]").getAttribute("data-semantic-result"));
    assert.equal(result.topology, topology);
    assert.ok(result.state.focusedStageId || result.state.selectedId);
  });

  await check("spatial fraction classification returns IDs rather than pixels", async () => {
    const article = page.locator('[data-canvas-pattern="SPATIAL_MANIPULATION"]');
    await article.getByRole("button", { name: "Place ¾ in < 1", exact: true }).press("Enter");
    assert.deepEqual(JSON.parse(await article.locator("[data-semantic-result]").getAttribute("data-semantic-result")), {
      objectId: "fraction-three-quarters",
      targetId: "less-than-one",
    });
  });

  await check("coordinate construction returns exact application integers in LTR math", async () => {
    const article = page.locator('[data-canvas-pattern="MATH_VISUALIZATION"]');
    await article.getByRole("spinbutton", { name: "X coordinate" }).fill("3");
    await article.getByRole("spinbutton", { name: "Y coordinate" }).fill("-1");
    assert.deepEqual(JSON.parse(await article.locator("[data-semantic-result]").getAttribute("data-semantic-result")), { x: 3, y: -1 });
    assert.equal(await article.locator(".jxgbox").evaluate((node) => getComputedStyle(node).direction), "ltr");
  });

  await check("MathLive edits and explicitly submits application-owned LaTeX", async () => {
    const article = page.locator('[data-canvas-pattern="MATH_INPUT"]');
    const field = article.locator("math-field");
    await field.click();
    await page.waitForFunction(() => document.activeElement?.tagName === "MATH-FIELD");
    await page.keyboard.press("End");
    await page.keyboard.type("+1");
    await page.waitForFunction(() => JSON.parse(document.querySelector('[data-canvas-pattern="MATH_INPUT"] [data-semantic-result]').getAttribute("data-semantic-result")).value.endsWith("+1"));
    await article.getByRole("button", { name: "Submit expression" }).click();
    const result = JSON.parse(await article.locator("[data-semantic-result]").getAttribute("data-semantic-result"));
    assert.deepEqual(result.submitted, { format: "latex", value: result.value });
  });

  await check("narrow and wide review remain usable without horizontal overflow", async () => {
    for (const width of [320, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      await page.waitForTimeout(100);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    }
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: path.join(evidence, "canvas-final-overview-wide.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(evidence, "canvas-final-overview-narrow.png"), fullPage: true });
  const shots = [
    ["process-sequence.png", '[data-process-topology="sequence"]'],
    ["process-cycle.png", '[data-process-topology="cycle"]'],
    ["spatial-manipulation.png", '[data-canvas-pattern="SPATIAL_MANIPULATION"]'],
    ["math-construction.png", '[data-canvas-pattern="MATH_VISUALIZATION"]'],
    ["math-expression.png", '[data-canvas-pattern="MATH_INPUT"]'],
  ];
  for (const [file, selector] of shots) await page.locator(selector).screenshot({ path: path.join(evidence, file) });

  await browser.close();
  fs.writeFileSync(path.join(evidence, "results.json"), JSON.stringify({
    supportedPatterns: ["PROCESS", "SPATIAL_MANIPULATION", "MATH_VISUALIZATION", "MATH_INPUT"],
    semanticContracts: {
      PROCESS: { input: { type: "explain_process", topology: "sequence | cycle" }, output: { topology: "sequence | cycle", state: "ProcessViewState", explanationStageId: "string | null" } },
      SPATIAL_MANIPULATION: { input: { type: "place_object", relation: "inside" }, output: { objectId: "string", targetId: "string | null" } },
      MATH_VISUALIZATION: { input: { type: "construct_coordinate", domain: "integer_grid" }, output: { x: "integer -4..4", y: "integer -4..4" } },
      MATH_INPUT: { input: { type: "author_math", format: "latex" }, output: { format: "latex", value: "string" } },
    },
    environment: "Isolated real Chrome with emulated touch; actual production components; no Student data, provider calls or persistence",
    results,
    errors,
    badAssets,
  }, null, 2) + "\n");
  assert.deepEqual(errors, []);
  assert.deepEqual(badAssets, []);
  assert.equal(results.filter((result) => !result.pass).length, 0);
})().catch((error) => { console.error(error); process.exitCode = 1; });
