const { chromium } = require("playwright");
const assert = require("node:assert/strict"); const fs = require("node:fs"); const path = require("node:path");
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true }); const page = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const evidence = path.resolve(process.env.CANVAS_VISUAL_EVIDENCE || "output/playwright/canvas-visual-intelligence"); fs.mkdirSync(evidence, { recursive: true }); const results = [], screenshots = [], measurements = [], errors = [], badAssets = [];
  page.on("pageerror", error => errors.push(error.message)); page.on("response", response => { if (response.status() >= 400) badAssets.push({ status: response.status(), url: response.url() }); });
  const shot = async (name, fullPage = true) => { const file = `${name}.png`; await page.screenshot({ path: path.join(evidence, file), fullPage }); screenshots.push(file); };
  const check = async (name, fn) => { try { await fn(); results.push({ name, pass: true }); } catch (error) { results.push({ name, pass: false, error: error.message }); } };
  await page.goto(process.env.CANVAS_VISUAL_URL || "http://127.0.0.1:5084"); await page.waitForSelector('[data-pattern="NUMBER_LINE"]');
  await check("NUMBER_LINE renders actual line geometry", async () => { assert.equal(await page.locator('[data-agentic-surface="number-line"]').count(), 1); assert.equal(await page.locator('[data-agentic-surface="number-line"] line').count() > 3, true); }); await shot("number-line-narrow");
  await page.getByRole("button", { name: "PLOT", exact: true }).click(); await check("PLOT renders a coordinate graph, not a number line", async () => { assert.equal(await page.locator('[data-agentic-surface="plot"]').count(), 1); assert.equal(await page.locator('[data-agentic-surface="number-line"]').count(), 0); assert.equal(await page.locator('[data-agentic-surface="plot"] line').count() > 10, true); }); await shot("plot-narrow");
  await page.getByRole("button", { name: "CYCLE", exact: true }).click(); await page.waitForTimeout(600); await check("CYCLE uses connected radial geometry and finite reveal", async () => { assert.equal(await page.locator('[data-agentic-surface="diagram"][data-topology="CYCLE"]').count(), 1); assert.equal(await page.locator('[data-agentic-revealed="true"]').count(), 1); assert.equal(await page.locator('[data-agentic-layout="FOCUS"][data-agentic-motion="REVEAL"]').count(), 1); }); await shot("cycle-revealed");
  await page.getByRole("button", { name: "SHAPES", exact: true }).click(); await check("SCENE_2D retains polygon, arrow, and label primitives", async () => { assert.equal(await page.locator('[data-object-kind="POLYGON"] polygon').count(), 1); assert.equal(await page.locator('[data-object-kind="ARROW"] line').count(), 1); assert.equal(await page.locator('[data-object-kind="LABEL"] rect').count(), 0); }); await shot("scene-2d-shapes");
  await page.getByRole("button", { name: "ARABIC", exact: true }).click(); await page.waitForTimeout(600); await check("Arabic scene keeps RTL and focus-support composition", async () => { assert.equal(await page.locator('[data-pattern="ARABIC"]').getAttribute("dir"), "rtl"); assert.equal(await page.locator('[data-agentic-layout="FOCUS_SUPPORT"]').count(), 1); assert.match(await page.locator('[data-objective]').innerText(), /رتّب/); }); await shot("arabic-rtl");
  await page.getByRole("button", { name: "OLDER", exact: true }).click(); await check("older learner presentation preserves math truth with denser GRID support", async () => { assert.equal(await page.locator('[data-agentic-layout="GRID"]').count(), 1); assert.match(await page.locator('[data-objective]').innerText(), /same fractions/); assert.equal(await page.locator('[data-agentic-surface="number-line"]').count(), 1); });
  await page.getByRole("button", { name: "ATOM", exact: true }).click(); await shot("atom-fractional-before");
  await page.getByRole("button", { name: "ATOM_FIXED", exact: true }).click();
  for (const [name, width, height] of [["desktop", 1440, 900], ["ipad-portrait-emulation", 768, 1024], ["ipad-landscape-emulation", 1024, 768]]) {
    await page.setViewportSize({ width, height });
    const measure = await page.evaluate(() => {
      const shell = document.querySelector(".daily-shell");
      const svg = document.querySelector('[data-agentic-surface="scene-2d"]');
      const labels = [...document.querySelectorAll('[data-agentic-surface="scene-2d"] [data-object-kind] text')].map(node => { const box = node.getBoundingClientRect(); return { text: node.textContent, x: box.x, y: box.y, width: box.width, height: box.height, fontPx: parseFloat(getComputedStyle(node).fontSize) }; });
      const caption = document.querySelector('[data-agentic-relation] text').getBoundingClientRect();
      const circles = [...document.querySelectorAll('[data-object-kind="CIRCLE"] circle')].map(node => { const box = node.getBoundingClientRect(); return { x: box.x, y: box.y, width: box.width, height: box.height }; });
      return { paneWidth: shell.getBoundingClientRect().width, svgWidth: svg.getBoundingClientRect().width, labels, caption: { x: caption.x, y: caption.y, width: caption.width, height: caption.height }, circles };
    });
    measurements.push({ name, viewport: { width, height }, ...measure });
    await check(`${name} atom labels are readable and separate`, async () => {
      assert.equal(measure.labels.length, 3);
      assert.equal(measure.labels.every(label => label.fontPx >= 16 && label.height >= 15), true);
      assert.equal(measure.labels[0].x + measure.labels[0].width < measure.labels[1].x, true);
      assert.equal(measure.labels[1].x + measure.labels[1].width < measure.labels[2].x, true);
      assert.equal(measure.circles.every(circle => measure.caption.y + measure.caption.height < circle.y), true);
      const line = await page.locator('[data-agentic-relation] line').evaluate(node => ({ end: Number(node.getAttribute('x2')), target: Number(document.querySelector('[data-object-kind="CIRCLE"]:last-of-type circle')?.getAttribute('cx')) }));
      assert.equal(line.end < line.target, true);
    });
    await shot(`atom-fixed-${name}`);
  }
  await page.getByRole("button", { name: "IMAGE", exact: true }).click();
  await page.locator('img[alt*="two green leaves"]').waitFor();
  await page.waitForTimeout(350);
  await check("owned image is primary with relevant interaction support", async () => { assert.equal(await page.locator('[data-agentic-region="focus"] img').count(), 1); assert.equal(await page.locator('[data-agentic-region="support-rail"] [data-text-group]').count(), 2); assert.equal(await page.locator('img[alt*="branching roots"]').evaluate(image => image.complete && image.naturalWidth > 0), true); });
  await shot("owned-image-primary-desktop");
  for (const [name, width, height] of [["ipad-portrait-emulation", 768, 1024], ["ipad-landscape-emulation", 1024, 768]]) { await page.setViewportSize({ width, height }); await shot(`owned-image-primary-${name}`, false); await page.locator('[data-agentic-region="support-rail"]').scrollIntoViewIfNeeded(); await shot(`owned-image-support-${name}`, false); }
  await check("image support permits one touch-sized semantic move", async () => { const button = page.getByRole("button", { name: "Place in Above soil" }).first(); const box = await button.boundingBox(); assert.ok(box && box.height >= 40); await button.click(); await page.waitForFunction(() => document.querySelector('[data-last-operation]')?.textContent?.includes("MOVE")); assert.match(await page.locator('[data-last-operation]').innerText(), /MOVE:leaves:above/); });
  await check("narrow and wide production renderer layouts avoid page overflow", async () => { for (const width of [320, 1280]) { await page.setViewportSize({ width, height: 900 }); await page.waitForTimeout(80); assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true); } }); await page.setViewportSize({ width: 1280, height: 900 }); await shot("older-wide");
  await browser.close(); const payload = { environment: "Authenticated-independent Chrome harness mounting the exact production StudioRendererHost; no Clerk session or Daily login; iPad viewports are emulated", host: "StudioRendererHost", results, screenshots, measurements, errors, badAssets }; fs.writeFileSync(path.join(evidence, "results.json"), JSON.stringify(payload, null, 2) + "\n"); assert.equal(results.filter(result => !result.pass).length, 0, JSON.stringify(results)); assert.deepEqual(errors, []); assert.deepEqual(badAssets, []);
})().catch(error => { console.error(error); process.exitCode = 1; });
