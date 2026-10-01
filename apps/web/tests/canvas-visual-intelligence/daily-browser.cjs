const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const sessionId = "11111111-1111-4111-8111-111111111111";
const runtimeId = "22222222-2222-4222-8222-222222222222";
const proofRoot = path.resolve(__dirname, "../../../../output/playwright/tutor-canvas-image-live");
const imageScene = JSON.parse(fs.readFileSync(process.env.CANVAS_IMAGE_SCENE || path.join(proofRoot, "adopted-scene.json"), "utf8"));
function findOwnedData(dir, assetId) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const child = path.join(dir, entry.name);
    if (entry.name === assetId && fs.existsSync(path.join(child, "image.object", "data"))) return path.join(child, "image.object", "data");
    const found = findOwnedData(child, assetId);
    if (found) return found;
  }
  return null;
}
const ownedData = process.env.CANVAS_OWNED_IMAGE || findOwnedData(path.join(proofRoot, "owned"), imageScene.blocks[0].studio_generated_asset_id);
if (!ownedData) throw new Error("The local owned-image proof must be provided before running this fixture.");
const generatedImage = fs.readFileSync(ownedData);
const base = { meaning: "Observe the relationship.", accessibility: { text_equivalent: "A visual explaining the relationship.", aria_label: "Educational visual" }, allowed_actions: [], elements: [] };
const atomScene = { version: "agentic-canvas-scene-v2", objective: "بيّن كيف تهتز الذرة بين موضعين قريبين.", subject_key: "SCIENCE",
  presentation: { layout: "FOCUS", palette: "COOL", motion: "NONE", placements: [{ block_id: "atom", role: "PRIMARY", order: 0, span: "FULL" }], reveal_order: [] },
  blocks: [{ ...base, block_id: "atom", type: "SCENE_2D", title: "اهتزاز الذرة", viewport_width_units: 100, viewport_height_units: 100,
    objects: [{ id: "left", label: "الموضع الأول", object_kind: "CIRCLE", position: { x: "35", y: "50" }, draggable: false },
      { id: "center", label: "الذرة", object_kind: "CIRCLE", position: { x: "50", y: "50" }, draggable: false },
      { id: "right", label: "الموضع الثاني", object_kind: "CIRCLE", position: { x: "65", y: "50" }, draggable: false }],
    relations: [{ source_id: "left", target_id: "right", relation: "MOVES_TOWARD", label: "حركة ذهاب وإياب" }] }] };
const seedScene = { version: "agentic-canvas-scene-v3", objective: "شاهدي مراحل نمو البذرة خطوة بخطوة.", subject_key: "SCIENCE",
  presentation: { layout: "FOCUS", palette: "NATURE", motion: "NONE", placements: [{ block_id: "growth", role: "PRIMARY", order: 0, span: "FULL" }], reveal_order: [] },
  blocks: [{ block_id: "growth", type: "CUSTOM_VISUAL", title: "نمو البذرة", meaning: "انتقلي بين ثلاث مراحل لنمو البذرة.", accessibility: { text_equivalent: "بذرة ثم جذر ثم نبتة صغيرة.", aria_label: "مراحل نمو البذرة" },
    allowed_actions: ["STEP"], elements: [{ id: "stage", label: "مرحلة النمو", current_value: "0" }], artifact_instance_id: "synthetic-seed-growth", bridge_nonce: "daily-seed-nonce", custom_visual_build_id: "33333333-3333-4333-8333-333333333333", manifest_digest: "a".repeat(64), parameters: {},
    semantic_interactions: [{ semantic_id: "stage", action: "STEP", value_required: true }] }] };
const imageCustomScene = { ...imageScene, version: "agentic-canvas-scene-v3", blocks: [imageScene.blocks[0], seedScene.blocks[0]],
  presentation: { layout: "FOCUS_SUPPORT", palette: "NATURE", motion: "NONE", placements: [
    { block_id: imageScene.blocks[0].block_id, role: "PRIMARY", order: 0, span: "WIDE" },
    { block_id: "growth", role: "INTERACTION", order: 1, span: "NORMAL" },
  ], reveal_order: [] } };
const seedSource = `window.mount=(root,p,bridge)=>{let n=Number(bridge.read('stage',0));const stages=['بذرة','جذر','نبتة صغيرة'];const wrap=document.createElement('main');wrap.dir='rtl';wrap.style='box-sizing:border-box;min-height:300px;padding:24px;background:#f0fdf4;color:#173d3a;font:24px Arial;text-align:center';const title=document.createElement('h1');title.textContent='نمو البذرة';const picture=document.createElement('div');picture.style='font-size:80px;margin:20px';const label=document.createElement('p');const button=document.createElement('button');button.textContent='المرحلة التالية';button.style='min-height:48px;padding:8px 18px;font:20px Arial';const control=bridge.control(button,'stage','STEP');const render=()=>{picture.textContent=['🫘','🌱','🌿'][n%3];label.textContent=stages[n%3]};button.onclick=()=>{n=(n+1)%3;control.emit(String(n));render()};wrap.append(title,picture,label,button);root.append(wrap);render()}`;
function snapshot(scene, name) { const version = scene.version.endsWith("-v3") ? "v3" : "v2"; return { protocol_version: "studio-protocol-v1", type: "STUDIO_SNAPSHOT", latest_event_sequence: 0, snapshot_schema_version: "studio-snapshot-v1", current_scene_id: `scene-${name}`, current_scene_version: 1, active_subject_key: "CANVAS", active_activity_key: "agentic_canvas", active_step_key: null, state_payload: { agentic_canvas: scene }, active_scene_seed: scene, active_scene_contract: { scene_id: `scene-${name}`, scene_version: 1, subject_key: "CANVAS", subject_profile_version: `agentic-canvas-profile-${version}`, activity_key: "agentic_canvas", activity_contract_version: "agentic-canvas-activity-v1", renderer_key: "agentic-canvas", renderer_version: `agentic-canvas-renderer-${version}`, payload_schema_version: scene.version, locale: "ar", direction: "rtl" } }; }
function composition(name, status = "COMPLETED") { return { version: "canvas-composition-view-v1", observed_at: new Date().toISOString(), runtime_id: runtimeId, run_id: name === "solar" ? "solar-run" : `${name}-run`, run_created_at: name === "solar" ? new Date().toISOString() : "2026-09-29T11:30:00Z", source_message_id: null, run_status: status, job_status: status, objective: name === "solar" ? "Solar-system model" : "Current visual", scene_id: status === "COMPLETED" ? `scene-${name}` : null, scene_ready: status === "COMPLETED", active_scene_id: `scene-${name === "solar" ? "seed" : name}`, active_scene_version: 1, deadline_at: null, failure_code: null }; }
const sse = (event, value) => `event: ${event}\ndata: ${JSON.stringify(value)}\n\n`;

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: "ar-SA", hasTouch: true });
  await page.addInitScript(() => { window.process = { env: { NEXT_PUBLIC_APP_ENV: "test", NEXT_PUBLIC_API_BASE_URL: "/api" } }; });
  page.setDefaultTimeout(7_000);
  const evidence = path.resolve(process.env.CANVAS_DAILY_EVIDENCE || "output/playwright/tutor-canvas-daily-local"); fs.mkdirSync(evidence, { recursive: true });
  const errors = [], badAssets = [], screenshots = [], measurements = [], checks = [];
  let name = "atom", solarAttempts = 0, operationCount = 0, scene = atomScene, pendingSolar = false;
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("response", response => { if (response.status() >= 400) badAssets.push({ status: response.status(), url: response.url() }); });
  await page.route("**/api/v1/student/**", async route => {
    const url = new URL(route.request().url()); const pathname = url.pathname;
    const json = value => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(value) });
    if (pathname.endsWith("/daily/session") && route.request().method() === "POST") return json({ learning_session_id: sessionId, status: "OPEN", messages: name === "seed" ? [{ id: "prior-seed-turn", role: "student", content: "أريد صورة خطوة بخطوة لنمو البذرة", created_at: "2026-09-29T11:31:00Z", suggested_actions: [] }, { id: "prior-seed-reply", role: "tutor", content: "شاهدي مراحل النمو في Canvas.", created_at: "2026-09-29T11:32:00Z", suggested_actions: [] }] : [] });
    if (pathname.includes("/studio/session/") && pathname.endsWith("/open")) return json({ runtime_id: runtimeId, learning_session_id: sessionId, status: "OPEN", latest_event_sequence: 0 });
    if (pathname.endsWith("/snapshot")) return json(snapshot(scene, name));
    if (pathname.endsWith("/composition-status")) return json(composition(pendingSolar ? "solar" : name, pendingSolar ? "PENDING" : "COMPLETED"));
    if (pathname.includes("/events/stream")) return route.fulfill({ status: 200, contentType: "text/event-stream", body: ": fixture\n\n" });
    if (pathname.includes("/custom-visual-builds/")) return json({ source: seedSource, manifest: { interactions: [{ action: "STEP", semantic_id: "stage", value_required: true }] } });
    if (pathname.includes("/assets/")) return route.fulfill({ status: 200, contentType: "image/png", body: generatedImage });
    if (pathname.endsWith("/operations")) { operationCount++; return json({ event_id: `event-${operationCount}`, sequence: operationCount, replayed: false, student_interaction_id: null, student_interaction_status: null }); }
    if (pathname.endsWith("/turn/stream")) {
      solarAttempts++;
      const body = solarAttempts === 1 ? sse("delta", { text: "Unvalidated partial" }) + sse("error", { code: "TUTOR_TURN_REJECTED" }) : solarAttempts === 2 ? "" : sse("turn", { text: "لعمل نموذج للمجموعة الشمسية، ابدئي بالشمس ثم رتّبي الكواكب حولها حسب بعدها.", suggested_actions: [], canvas_composition: composition("solar", "PENDING") });
      if (solarAttempts === 3) pendingSolar = true;
      return route.fulfill({ status: 200, contentType: "text/event-stream", headers: { "X-Lina-Student-Message-ID": `durable-solar-${solarAttempts}` }, body });
    }
    throw new Error(`Unexpected fixture API: ${pathname}`);
  });
  const goto = async next => { name = next; scene = next === "seed" ? seedScene : next === "image" ? imageScene : next === "image-custom" ? imageCustomScene : atomScene; pendingSolar = false; await page.goto(`http://127.0.0.1:5087/?fixture=${next}`); try { await page.locator('aside[aria-label="مساحة Canvas التعليمية"]').waitFor(); } catch (error) { console.error({ body: (await page.locator("body").innerText()).slice(0, 1000), errors, badAssets }); throw error; } };
  const shot = async (file, fullPage = true) => { await page.screenshot({ path: path.join(evidence, `${file}.png`), fullPage }); screenshots.push(`${file}.png`); };
  const check = async (label, run) => { try { await run(); checks.push({ label, pass: true }); } catch (error) { checks.push({ label, pass: false, error: error.message }); } };
  for (const [caseName, width, height] of [["desktop", 1440, 900], ["ipad-portrait-emulation", 768, 1024], ["ipad-landscape-emulation", 1024, 768]]) {
    await page.setViewportSize({ width, height }); await goto("atom"); await page.locator('[data-agentic-surface="scene-2d"]').waitFor();
    const measure = await page.evaluate(() => { const pane = document.querySelector('aside[aria-label="مساحة Canvas التعليمية"]'); const svg = document.querySelector('[data-agentic-surface="scene-2d"]'); const labels = [...svg.querySelectorAll('[data-object-kind] text')].map(node => { const r = node.getBoundingClientRect(); return { text: node.textContent, x: r.x, right: r.right, y: r.y, width: r.width, fontPx: Number.parseFloat(getComputedStyle(node).fontSize) }; }); return { pane: pane.getBoundingClientRect().width, svg: svg.getBoundingClientRect().width, labels, pageOverflow: document.documentElement.scrollWidth > innerWidth }; });
    measurements.push({ caseName, viewport: { width, height }, ...measure });
    await check(`${caseName} actual Daily atom pane`, async () => { assert.ok(measure.pane > 600); assert.ok(measure.svg >= 600); assert.equal(measure.pageOverflow, false); assert.equal(measure.labels.length, 3); assert.ok(measure.labels.every(label => label.fontPx >= 16)); assert.ok(measure.labels[0].right < measure.labels[1].x && measure.labels[1].right < measure.labels[2].x); });
    await shot(`daily-atom-${caseName}`);
  }
  await page.setViewportSize({ width: 768, height: 1024 }); await goto("seed"); try { await page.locator('[data-custom-visual-sandbox="ready"]').waitFor(); } catch (error) { console.error({ seedBody: (await page.locator("body").innerText()).slice(0, 1500), sandboxStates: await page.locator('[data-custom-visual-sandbox]').evaluateAll(nodes => nodes.map(node => node.getAttribute('data-custom-visual-sandbox'))), errors, badAssets }); throw error; }
  await check("synthetic seed custom visual fits actual Daily pane", async () => { const iframe = page.locator('iframe[title="نمو البذرة"]'); const pane = page.locator('aside[aria-label="مساحة Canvas التعليمية"]'); const [frameBox, paneBox] = await Promise.all([iframe.boundingBox(), pane.boundingBox()]); assert.ok(frameBox && paneBox && frameBox.width > 500 && frameBox.width <= paneBox.width); assert.equal(await iframe.getAttribute("sandbox"), "allow-scripts"); });
  await shot("daily-synthetic-seed-ipad-portrait-emulation");
  await check("seed step is usable through sandbox and server operation", async () => { await Promise.all([page.waitForResponse(response => response.url().endsWith("/operations")), page.frameLocator('iframe[title="نمو البذرة"]').getByRole("button", { name: "المرحلة التالية" }).click()]); assert.equal(operationCount, 1); });
  await goto("image"); await page.locator('img[alt*="two green leaves"]').waitFor();
  await check("owned image renders through real Daily asset loader", async () => { const image = page.locator('img[alt*="branching roots"]'); assert.equal(await image.evaluate(node => node.complete && node.naturalWidth > 0), true); assert.equal(await page.locator('[data-agentic-region="support-rail"] [data-text-group]').count(), 2); });
  await shot("daily-owned-image-ipad-portrait-emulation");
  await goto("image-custom"); await page.locator('[data-custom-visual-sandbox="ready"]').waitFor(); await page.frameLocator('iframe[title="نمو البذرة"]').getByRole("button", { name: "المرحلة التالية" }).waitFor();
  await check("v3 image and custom interaction share the Daily composition", async () => { assert.equal(await page.locator('[data-agentic-region="focus"] img[alt*="branching roots"]').count(), 1); assert.equal(await page.locator('[data-agentic-region="support-rail"] [data-custom-visual-sandbox="ready"]').count(), 1); assert.equal(await page.frameLocator('iframe[title="نمو البذرة"]').getByText("بذرة", { exact: true }).count(), 1); assert.equal(await page.getByText("This Canvas scene could not be opened safely.").count(), 0); });
  await page.locator('iframe[title="نمو البذرة"]').scrollIntoViewIfNeeded(); await shot("daily-v3-image-custom-ipad-portrait-emulation", false);
  await check("v3 combined custom control reaches one Studio operation", async () => { await Promise.all([page.waitForResponse(response => response.url().endsWith("/operations")), page.frameLocator('iframe[title="نمو البذرة"]').getByRole("button", { name: "المرحلة التالية" }).click()]); assert.equal(operationCount, 2); });
  await goto("seed");
  for (let attempt = 1; attempt <= 3; attempt++) {
    await page.getByLabel("رسالتك إلى لينا").fill("كيف أصنع نموذجًا للمجموعة الشمسية؟"); await page.getByRole("button", { name: "إرسال", exact: true }).click();
    await page.waitForFunction(expected => document.querySelectorAll('article').length >= expected, attempt + 2);
    try { await page.waitForFunction(() => !document.querySelector('#daily-learning-message')?.disabled); } catch (error) { console.error({ attempt, solarAttempts, body: (await page.locator("body").innerText()).slice(-1600), errors, badAssets }); throw error; }
    if (attempt < 3) await check(`failure ${attempt} is terminal and preserves Student input`, async () => { assert.equal(await page.locator('[role="alert"]').filter({ hasText: /لم يكتمل|لم أستطع/ }).count() > 0, true); assert.equal(await page.getByText("Unvalidated partial").count(), 0); assert.equal(await page.getByText("كيف أصنع نموذجًا للمجموعة الشمسية؟").count(), attempt); });
  }
  await page.getByText(/لعمل نموذج للمجموعة الشمسية/).waitFor();
  await check("successful retry marks prior seed work as updating", async () => { assert.equal(solarAttempts, 3); assert.equal(await page.getByText(/لعمل نموذج للمجموعة الشمسية/).count(), 1); assert.equal(await page.getByText("جارٍ تجهيز تحديث بصري").count(), 1); assert.equal(await page.locator('[data-custom-visual-sandbox="ready"]').count(), 1); assert.equal(operationCount, 2); });
  await shot("daily-seed-to-solar-successful-retry");
  await browser.close();
  const result = { environment: "Real DailyStudentApp and production Tailwind CSS with synthetic API/Clerk data; iPad sizes are Chrome emulation, seed Scene is synthetic, no production learner or provider call", checks, measurements, screenshots, solarAttempts, operationCount, errors, badAssets };
  fs.writeFileSync(path.join(evidence, "results.json"), JSON.stringify(result, null, 2) + "\n");
  assert.equal(checks.filter(check => !check.pass).length, 0, JSON.stringify(checks)); assert.deepEqual(errors, []); assert.deepEqual(badAssets, []);
})().catch(error => { console.error(error); process.exitCode = 1; });
