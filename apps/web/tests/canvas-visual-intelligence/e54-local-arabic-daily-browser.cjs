/** Render accepted E52 Arabic typed Scene in the real Daily component. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(process.env.CANVAS_VISUAL_HARNESS || "/private/tmp/lina-e54-local-daily");
const out = path.resolve("output/visual-teacher-e54-local/arabic-daily-browser");
const transport = JSON.parse(fs.readFileSync(
  path.resolve("output/visual-teacher-e52-live-current/arabic-sentence-daily-transport-private.json"),
  "utf8",
));
fs.mkdirSync(out, { recursive: true });

let operationCount = 0;
let tutorCount = 0;
const server = http.createServer((request, response) => {
  const pathname = new URL(request.url, "http://127.0.0.1").pathname;
  const file = path.join(root, pathname === "/" ? "index.html" : pathname);
  if (!file.startsWith(root) || !fs.existsSync(file)) {
    response.writeHead(404); response.end(); return;
  }
  response.setHeader("Content-Type", file.endsWith(".js") ? "text/javascript" : file.endsWith(".css") ? "text/css" : "text/html");
  response.end(fs.readFileSync(file));
});


(async () => {
  await new Promise(resolve => server.listen(5091, "127.0.0.1", resolve));
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.addInitScript(() => {
    window.process = { env: { NEXT_PUBLIC_APP_ENV: "test", NEXT_PUBLIC_API_BASE_URL: "/api" } };
  });
  page.setDefaultTimeout(15_000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));

  await page.route("**/api/v1/student/**", async route => {
    const name = new URL(route.request().url()).pathname;
    const json = value => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(value),
    });
    if (name.endsWith("/daily/session") && route.request().method() === "POST")
      return json({ learning_session_id: transport.learning_session_id, status: "OPEN", messages: [] });
    if (name.endsWith("/open"))
      return json({ runtime_id: transport.runtime_id, learning_session_id: transport.learning_session_id, status: "OPEN", latest_event_sequence: transport.snapshot.latest_event_sequence });
    if (name.endsWith("/snapshot")) return json(transport.snapshot);
    if (name.endsWith("/composition-status")) return json(transport.composition_status);
    if (name.includes("/events/stream"))
      return route.fulfill({ status: 200, contentType: "text/event-stream", body: ": idle\n\n" });
    if (name.endsWith("/operations")) operationCount++;
    if (name.endsWith("/turn/stream")) tutorCount++;
    throw Error(`Unexpected browser API request: ${name}`);
  });


  const measurements = [];
  for (const [label, width, height] of [
    ["desktop", 1440, 900],
    ["tablet-portrait-emulation", 768, 1024],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("http://127.0.0.1:5091/");
    const pane = page.locator('aside[aria-label="Learning Canvas"]');
    await pane.waitFor();
    await page.getByText("رتّب الكلمات", { exact: true }).waitFor();
    await page.getByText("ميّز وظيفة كل كلمة", { exact: true }).waitFor();
    assert.equal(await page.getByText(/Ordering is not available safely in Canvas yet/).count(), 0);
    await page.getByText("إرسال الترتيب", { exact: true }).waitFor();
    await page.getByText("الخيارات", { exact: true }).waitFor();
    const orderIds = await pane.locator("[data-order-item]").evaluateAll((elements) => elements.map((element) => element.getAttribute("data-order-item")));
    assert.notDeepEqual(orderIds, ["verb", "subject", "object"]);
    const paneBox = await pane.boundingBox();
    assert.ok(paneBox && paneBox.width > 250);
    const text = (await pane.innerText()).slice(0, 3000);
    assert.doesNotMatch(text, /Place in|Choices|Ordering is not available safely/);
    await page.screenshot({ path: path.join(out, label + ".png"), fullPage: false });
    await pane.screenshot({ path: path.join(out, label + "-canvas-pane.png") });
    measurements.push({ label, viewport: [width, height], pane: paneBox, text });
  }

  assert.equal(operationCount, 0);
  assert.equal(tutorCount, 0);
  assert.deepEqual(errors, []);
  fs.writeFileSync(path.join(out, "results.json"), JSON.stringify({
    measurements, operationCount, tutorCount, errors,
    environment: "Real Daily component and CSS; exact owner-scoped typed Scene as browser transport fixture.",
  }, null, 2));
  await browser.close();
  server.close();
})().catch(error => {
  console.error(error);
  server.close();
  process.exit(1);
});
