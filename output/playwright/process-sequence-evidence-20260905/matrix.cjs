// Actual Chromium input matrix for the isolated Process Sequence review mount.
// The page labels its controller as mock; this script makes no persistence claim.
const { chromium } = require(process.env.PROCESS_SEQUENCE_PLAYWRIGHT);
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const prepare = "prepare-filter-funnel";
const initialOrder = [
  "allow-water-to-filter",
  prepare,
  "collect-filtered-water",
  "pour-sand-water-mixture",
];
const movedOrder = [prepare, "allow-water-to-filter", "collect-filtered-water", "pour-sand-water-mixture"];
const expectedReorder = { stage_id: prepare, from_index: 1, to_index: 0 };
const cases = [
  "mouse-center",
  "mouse-edge",
  "touch-center",
  "touch-edge",
  "keyboard",
  "touch-cancel-retry",
  "capture-loss-retry",
  "mouse-outside-retry",
  "touch-outside-retry",
  "rejection",
  "arabic-rtl-narrow-touch",
  "reduced-motion",
];

function isTouch(name) {
  return name.includes("touch");
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const name of cases) {
    const arabic = name === "arabic-rtl-narrow-touch";
    const touch = isTouch(name);
    const context = await browser.newContext({
      hasTouch: touch,
      viewport: { width: arabic ? 390 : 1280, height: 1200 },
      reducedMotion: name === "reduced-motion" ? "reduce" : "no-preference",
    });
    const page = await context.newPage();
    const result = {
      name,
      transport: "isolated review mock only",
      method: touch ? "Trusted Chromium CDP touch input" : name === "keyboard" || name === "reduced-motion" ? "Browser keyboard Enter" : "Native browser mouse input",
    };
    const cdp = touch ? await context.newCDPSession(page) : null;
    try {
      await page.goto(`http://127.0.0.1:5001/studio/process-sequence-review?locale=${arabic ? "ar" : "en"}&direction=${arabic ? "rtl" : "ltr"}${name === "rejection" ? "&reject_operation=1" : ""}`);
      await page.locator('output[data-operation-trace="[]"]').waitFor();
      await page.evaluate(() => {
        window.processSequenceEvents = [];
        for (const type of ["pointerdown", "pointerup", "pointercancel", "gotpointercapture", "lostpointercapture", "click", "keydown"]) {
          document.addEventListener(type, (event) => window.processSequenceEvents.push({
            type: event.type,
            trusted: event.isTrusted,
            pointerType: event.pointerType || null,
            pointerId: event.pointerId || null,
            key: event.key || null,
            target: event.target.tagName,
          }), true);
        }
      });
      const order = () => page.locator("[data-process-sequence-stage]").evaluateAll((nodes) => nodes.map((node) => node.dataset.processSequenceStage));
      const operations = async () => JSON.parse(await page.locator("output[data-operation-trace]").getAttribute("data-operation-trace"));
      const status = () => page.locator('[role="status"]').allTextContents();
      const geometry = async () => {
        const box = await page.locator(`[data-process-sequence-stage="${prepare}"]`).boundingBox();
        const target = await page.locator(`[data-process-sequence-stage="allow-water-to-filter"]`).boundingBox();
        assert(box && target);
        const edge = name.endsWith("edge");
        return {
          from: { x: box.x + box.width * (edge ? 0.15 : 0.5), y: box.y + box.height * 0.5 },
          to: { x: target.x + target.width * 0.5, y: target.y + target.height * 0.5 },
        };
      };
      const settle = () => page.waitForTimeout(150);
      const start = async (from) => {
        if (touch) return cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ ...from, id: 1 }] });
        await page.mouse.move(from.x, from.y);
        await page.mouse.down();
      };
      const move = async (from, to) => {
        if (touch) {
          for (let index = 1; index <= 12; index += 1) {
            await cdp.send("Input.dispatchTouchEvent", {
              type: "touchMove",
              touchPoints: [{ x: from.x + (to.x - from.x) * index / 12, y: from.y + (to.y - from.y) * index / 12, id: 1 }],
            });
          }
          return;
        }
        await page.mouse.move(to.x, to.y, { steps: 12 });
      };
      const end = async () => {
        if (touch) await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
        else await page.mouse.up();
        await settle();
      };
      const validDrag = async () => {
        const points = await geometry();
        await start(points.from);
        await move(points.from, points.to);
        await end();
      };

      result.before = await order();
      assert.deepEqual(result.before, initialOrder);
      await page.screenshot({ path: path.join(root, `${name}-before.png`), fullPage: true });

      if (name.includes("retry")) {
        const points = await geometry();
        await start(points.from);
        if (name === "touch-cancel-retry") {
          await cdp.send("Input.dispatchTouchEvent", { type: "touchCancel", touchPoints: [] });
        } else if (name === "capture-loss-retry") {
          await page.evaluate((stageId) => {
            const target = document.querySelector(`[data-process-sequence-stage="${stageId}"]`);
            const event = window.processSequenceEvents.findLast((item) => item.type === "pointerdown");
            target.releasePointerCapture(event.pointerId);
          }, prepare);
        } else {
          await move(points.from, { x: 10, y: 10 });
          await end();
        }
        await settle();
        result.aborted = { order: await order(), operations: await operations(), status: await status() };
        assert.deepEqual(result.aborted.order, initialOrder);
        assert.deepEqual(result.aborted.operations, []);
        await page.screenshot({ path: path.join(root, `${name}-aborted.png`), fullPage: true });
        await validDrag();
      } else if (name === "keyboard" || name === "reduced-motion") {
        const moveUp = page.getByRole("button", { name: arabic ? "حرّك للأعلى" : "Move up", exact: true }).nth(1);
        await moveUp.focus();
        result.focus = await moveUp.evaluate((node) => ({ focused: document.activeElement === node, visible: node.matches(":focus-visible"), outline: getComputedStyle(node).outlineStyle }));
        assert(result.focus.focused && result.focus.visible);
        await moveUp.press("Enter");
        await settle();
      } else {
        await validDrag();
      }

      result.after = await order();
      result.operations = await operations();
      result.statusText = await status();
      assert.equal(result.operations.length, 1);
      assert.equal(result.operations[0].action_key, "REORDER_STAGE");
      assert.deepEqual(result.operations[0].payload, expectedReorder);
      assert.equal(result.operations[0].scene_id, "review-process-sequence-scene");
      assert.equal(result.operations[0].base_scene_version, 2);
      if (name === "rejection") {
        assert.deepEqual(result.after, initialOrder);
        assert(result.statusText.some((text) => text.includes(arabic ? "لا يمكن" : "cannot be sent")));
      } else {
        assert.deepEqual(result.after, movedOrder);
      }
      assert(!result.operations.some((operation) => operation.action_key === "SUBMIT_CONFIGURATION"));

      if (arabic) {
        assert.equal(await page.locator("[dir]").getAttribute("dir"), "rtl");
        assert(await page.getByRole("heading", { name: "رتّب خطوات الترشيح" }).isVisible());
        assert.equal(await page.getByRole("button", { name: "تحقّق من ترتيبي", exact: true }).count(), 1);
        result.layout = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
        assert(result.layout.scrollWidth <= result.layout.width);
      }
      if (name === "reduced-motion") {
        result.motion = await page.evaluate(() => ({
          enabled: matchMedia("(prefers-reduced-motion: reduce)").matches,
          activeAnimations: document.getAnimations().length,
          controls: [...document.querySelectorAll("button")].map((node) => ({ transition: getComputedStyle(node).transitionProperty, animation: getComputedStyle(node).animationName })),
        }));
        assert(result.motion.enabled && result.motion.activeAnimations === 0);
        assert(result.motion.controls.every((control) => control.animation === "none" && control.transition === "none"));
        await page.getByRole("button", { name: "Check my sequence", exact: true }).press("Enter");
        await settle();
        result.explicitSubmit = await operations();
        assert.deepEqual(result.explicitSubmit.map((operation) => operation.action_key), ["REORDER_STAGE", "SUBMIT_CONFIGURATION"]);
        assert.deepEqual(result.explicitSubmit[1].payload, { stage_ids: movedOrder });
        assert.equal(result.explicitSubmit[1].base_scene_version, 3);
      }
      result.events = await page.evaluate(() => window.processSequenceEvents);
      if (touch) assert(result.events.some((event) => event.trusted && event.type === "pointerdown" && event.pointerType === "touch"));
      if (name === "touch-cancel-retry") assert(result.events.some((event) => event.trusted && event.type === "pointercancel"));
      result.status = "PASS";
    } catch (error) {
      result.status = "FAIL";
      result.error = String(error);
      result.events = await page.evaluate(() => window.processSequenceEvents).catch(() => []);
    }
    await page.screenshot({ path: path.join(root, `${name}-after.png`), fullPage: true });
    results.push(result);
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(root, "results.json"), JSON.stringify({
    browser: "installed Google Chrome via cached Playwright",
    transport: "isolated mock review mount only",
    results,
  }, null, 2));
  console.log(results.map((result) => ({ name: result.name, status: result.status, error: result.error, operations: result.operations?.length })));
  process.exitCode = results.every((result) => result.status === "PASS") ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
