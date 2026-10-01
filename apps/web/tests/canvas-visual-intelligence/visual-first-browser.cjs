/** Deterministic Daily UI contract check; real generation is proved separately. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const root = process.env.CANVAS_VISUAL_HARNESS || "/private/tmp/lina-visual-first-daily";
const evidence = path.resolve(process.env.CANVAS_VISUAL_FIRST_EVIDENCE || "output/visual-first-browser");
fs.mkdirSync(evidence, { recursive: true });
const sessionId = "11111111-1111-4111-8111-111111111111";
const runtimeId = "22222222-2222-4222-8222-222222222222";
const sceneId = "33333333-3333-4333-8333-333333333333";
const buildId = "44444444-4444-4444-8444-444444444444";
const block = {
  block_id: "addition", type: "CUSTOM_VISUAL", title: "7 + 5", meaning: "Seven blue and five amber counters.",
  accessibility: { text_equivalent: "Seven and five counters in separate groups.", aria_label: "Addition visual" },
  allowed_actions: ["SUBMIT", "OPEN_ATTEMPT", "TOGGLE"],
  elements: [{ id: "labels", label: "Show labels", current_value: null }, { id: "sum-question", label: "What is 7 + 5?", current_value: null }],
  artifact_instance_id: "visual-first-fixture", bridge_nonce: "visual-first-bridge-nonce", custom_visual_build_id: buildId,
  manifest_digest: "a".repeat(64), parameters: {},
  semantic_interactions: [{ semantic_id: "labels", action: "TOGGLE", value_required: true }, { semantic_id: "sum-question", action: "SUBMIT", value_required: true }],
};
const manifest = {
  version: "canvas-semantic-manifest-v1", brief_digest: "b".repeat(64), objective: "Add seven and five.",
  representation_summary: "Seven blue and five amber counters form twelve.", demonstrates: "7 + 5 = 12 by counting all counters.",
  interpretation_limits: "Color only separates the addends.", entities: [], relations: [], quantities: [], presentation_steps: [], calculated_results: [], visual_descriptions: [],
  interactions: [{ semantic_id: "labels", action: "TOGGLE", meaning: "Show group labels.", value_required: true, purpose: "LOCAL" },
    { semantic_id: "sum-question", action: "SUBMIT", meaning: "Submit the total.", value_required: true, purpose: "ANSWER" }],
  current_state_schema: { labels: "whether labels are visible" }, provenance: {},
  choice_questions: [{ semantic_id: "sum-question", prompt: "What is 7 + 5?", options: [
    { value: "12", label: "12" }, { value: "13", label: "13" }, { value: "17", label: "17" } ] }],
};
const source = `window.mount=(root,params,bridge)=>{let shown=false;let clicks=0;const wrap=document.createElement('main');wrap.style='box-sizing:border-box;min-height:280px;padding:24px;background:#f5f9ff;font:20px Arial;color:#153047';const title=document.createElement('h2');title.textContent='7 + 5';const groups=document.createElement('div');groups.style='display:flex;gap:24px;flex-wrap:wrap';for(const [count,color] of [[7,'#3674bf'],[5,'#c97927']]){const group=document.createElement('div');group.style='display:flex;flex-wrap:wrap;gap:5px;max-width:180px';for(let i=0;i<count;i++){const dot=document.createElement('span');dot.style='width:20px;height:20px;border-radius:50%;background:'+color;group.append(dot)}groups.append(group)}const note=document.createElement('p');const button=document.createElement('button');button.textContent='Show labels';button.style='min-height:48px;padding:8px 18px;font:18px Arial';button.onclick=()=>{shown=!shown;clicks++;note.textContent=shown?'7 blue + 5 amber':'Groups only';bridge.local('labels',shown?'shown':'hidden')};wrap.append(title,groups,note,button);root.append(wrap);note.textContent='Groups only'}`;
let version = 1, answer = null, operationCount = 0, chatState = null, chatCount = 0;
function scene() { return { version: "agentic-canvas-scene-v3", objective: "Add seven and five.", subject_key: "MATH",
  presentation: { layout: "FOCUS", palette: "COOL", motion: "NONE", placements: [{ block_id: "addition", role: "PRIMARY", order: 0, span: "FULL" }], reveal_order: [] },
  blocks: [{ ...block, elements: [block.elements[0], { ...block.elements[1], current_value: answer }] }] }; }
function snapshot() { const seed = scene(); return { protocol_version: "studio-protocol-v1", type: "STUDIO_SNAPSHOT", latest_event_sequence: operationCount,
  snapshot_schema_version: "studio-snapshot-v1", current_scene_id: sceneId, current_scene_version: version,
  active_subject_key: "CANVAS", active_activity_key: "agentic_canvas", active_step_key: null,
  state_payload: { agentic_canvas: seed }, active_scene_seed: seed,
  active_scene_contract: { scene_id: sceneId, scene_version: version, subject_key: "CANVAS", subject_profile_version: "agentic-canvas-profile-v3",
    activity_key: "agentic_canvas", activity_contract_version: "agentic-canvas-activity-v1", renderer_key: "agentic-canvas",
    renderer_version: "agentic-canvas-renderer-v3", payload_schema_version: "agentic-canvas-scene-v3", locale: "en", direction: "ltr" } }; }
const sse = (event, value) => `event: ${event}\ndata: ${JSON.stringify(value)}\n\n`;
const server = http.createServer((request, response) => { const pathname = new URL(request.url, "http://127.0.0.1").pathname;
  const file = path.join(root, pathname === "/" ? "index.html" : pathname);
  if (!file.startsWith(root) || !fs.existsSync(file)) { response.writeHead(404); response.end(); return; }
  response.setHeader("Content-Type", file.endsWith(".js") ? "text/javascript" : file.endsWith(".css") ? "text/css" : "text/html"); response.end(fs.readFileSync(file)); });

(async () => {
  await new Promise(resolve => server.listen(5088, "127.0.0.1", resolve));
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.addInitScript(() => { window.process = { env: { NEXT_PUBLIC_APP_ENV: "test", NEXT_PUBLIC_API_BASE_URL: "/api" } }; });
  page.setDefaultTimeout(10_000);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/api/v1/student/**", async route => {
    const url = new URL(route.request().url()), name = url.pathname;
    const json = value => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(value) });
    if (name.endsWith("/daily/session") && route.request().method() === "POST") return json({ learning_session_id: sessionId, status: "OPEN", messages: [] });
    if (name.endsWith("/open")) return json({ runtime_id: runtimeId, learning_session_id: sessionId, status: "OPEN", latest_event_sequence: operationCount });
    if (name.endsWith("/snapshot")) return json(snapshot());
    if (name.endsWith("/composition-status")) return json({ version: "canvas-composition-view-v1", observed_at: new Date().toISOString(), runtime_id: runtimeId,
      run_id: "visual-first-fixture-run", run_created_at: "2026-09-30T12:00:00Z", source_message_id: null,
      run_status: "COMPLETED", job_status: "COMPLETED", objective: "Add seven and five.", scene_id: sceneId,
      scene_ready: true, active_scene_id: sceneId, active_scene_version: version, deadline_at: null, failure_code: null });
    if (name.includes("/events/stream")) return route.fulfill({ status: 200, contentType: "text/event-stream", body: ": idle\n\n" });
    if (name.includes("/custom-visual-builds/")) return json({ source, manifest });
    if (name.endsWith("/operations")) {
      const body = route.request().postDataJSON(), action = body.payload.action;
      assert.equal(body.base_scene_version, version);
      if (action === "SUBMIT") { assert.equal(answer, null); answer = body.payload.to_value; assert.ok(["12", "13", "17"].includes(answer)); }
      else { assert.equal(action, "OPEN_ATTEMPT"); assert.equal(body.payload.from_value, answer); answer = null; }
      operationCount++; version++;
      await new Promise(resolve => setTimeout(resolve, 200));
      return json({ event_id: `event-${operationCount}`, sequence: operationCount, replayed: false,
        student_interaction_id: action === "SUBMIT" ? `interaction-${operationCount}` : null,
        student_interaction_status: action === "SUBMIT" ? "PENDING" : null });
    }
    if (name.endsWith("/turn/stream")) {
      if (name.includes("/daily/session/")) { chatState = route.request().postDataJSON().local_visual_state; chatCount++; }
      const text = name.includes("/interactions/") ? "Let's count both groups together." : "The labels show the two groups.";
      return route.fulfill({ status: 200, contentType: "text/event-stream", headers: { "X-Lina-Student-Message-ID": `student-${chatCount}` },
        body: sse("turn", { text, suggested_actions: [] }) });
    }
    throw Error(`Unexpected request: ${name}`);
  });
  const checks = [], measurements = [];
  for (const [label, width, height] of [["desktop", 1440, 900], ["tablet-portrait-emulation", 768, 1024]]) {
    await page.setViewportSize({ width, height }); await page.goto("http://127.0.0.1:5088/");
    try { await page.locator('[data-custom-visual-sandbox="ready"]').waitFor(); }
    catch (error) { console.error({ body: (await page.locator("body").innerText()).slice(0, 1400),
      sandbox: await page.locator("[data-custom-visual-sandbox]").evaluateAll(nodes => nodes.map(node => node.getAttribute("data-custom-visual-sandbox"))), errors }); throw error; }
    const frame = page.locator('iframe[title="7 + 5"]');
    const box = await frame.boundingBox(), pane = await page.locator('aside[aria-label="Learning Canvas"]').boundingBox();
    assert.ok(box && pane && box.width > 500 && box.width <= pane.width);
    await frame.scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(evidence, `${label}.png`), fullPage: false });
    await page.locator('aside[aria-label="Learning Canvas"]').screenshot({ path: path.join(evidence, `${label}-canvas-pane.png`) });
    measurements.push({ label, viewport: [width, height], pane_width: pane.width, visual_width: box.width });
    checks.push(`${label} readable visual pane`);
  }
  const local = page.frameLocator('iframe[title="7 + 5"]').getByRole("button", { name: "Show labels" });
  await local.click(); await local.click(); await local.click();
  await page.waitForTimeout(150);
  assert.equal(operationCount, 0);
  checks.push("local controls emit zero Studio operations");
  await page.locator("#daily-learning-message").fill("What do the labels mean?");
  await page.locator("form button[type=submit]").click();
  await page.getByText("The labels show the two groups.").waitFor();
  assert.deepEqual(chatState?.values, { labels: "shown" });
  assert.equal(chatState?.scene_id, sceneId); assert.equal(chatState?.scene_version, version);
  checks.push("Chat carries bounded Scene-bound local state");
  const choices = page.locator('[data-canvas-question="sum-question"]');
  await choices.getByRole("button", { name: "17" }).dblclick();
  await choices.getByText("Answer saved for this attempt.").waitFor();
  assert.equal(operationCount, 1); assert.equal(answer, "17");
  await page.reload(); await choices.getByText("Answer saved for this attempt.").waitFor();
  assert.equal(await choices.getByRole("button", { name: "12" }).isDisabled(), true);
  checks.push("first choice stays fixed after double click and reload");
  await choices.getByRole("button", { name: "New attempt" }).click();
  await choices.getByRole("button", { name: "12" }).click();
  await choices.getByText("Answer saved for this attempt.").waitFor();
  assert.equal(answer, "12"); assert.equal(operationCount, 3);
  checks.push("explicit new attempt permits another answer");
  await browser.close(); server.close();
  fs.writeFileSync(path.join(evidence, "results.json"), JSON.stringify({ checks, measurements, operationCount, chatState, errors, environment: "Real Daily component and CSS with deterministic API and custom visual fixture; Chrome tablet viewport emulation." }, null, 2));
  assert.deepEqual(errors, []);
})().catch(error => { console.error(error); server.close(); process.exit(1); });
