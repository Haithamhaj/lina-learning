// Actual Chromium input matrix for the isolated Sentence Ordering review mount.
// The page labels its controller as mock; this script makes no persistence claim.
const { chromium } = require(process.env.SENTENCE_ORDERING_PLAYWRIGHT);
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = __dirname;
const birds = "tok-c820";
const fly = "tok-43bd";
const over = "tok-7f2c";
const clouds = "tok-a91e";
const initialOrder = [clouds, birds, over, fly];
const movedOrder = [birds, clouds, over, fly];
const expectedReorder = { token_id: birds, from_index: 1, to_index: 0 };

// Each named case maps to one of the Product Owner's required evidence points.
const cases = [
  "mouse-center",
  "mouse-edge",
  "touch-center",
  "touch-edge",
  "keyboard-button-accessibility",
  "touch-cancel-retry",
  "mouse-outside-retry",
  "rejection-reconciliation",
  "explicit-submit-once",
  "english-ltr",
  "arabic-outer-tokens-ltr",
  "mixed-label-layout",
  "narrow-mobile",
  "reduced-motion-static",
  "answer-key-negative",
  "arabic-keyboard-focus",
];
const requestedCases = process.env.SENTENCE_ORDERING_CASES?.split(",").filter(Boolean);
const selectedCases = requestedCases ? cases.filter((name) => requestedCases.includes(name)) : cases;

function usesTouch(name) {
  return name.startsWith("touch");
}

function isArabic(name) {
  return name === "arabic-outer-tokens-ltr" || name === "mixed-label-layout" || name === "narrow-mobile" || name === "arabic-keyboard-focus";
}

function caseViewport(name) {
  return name === "narrow-mobile" ? { width: 390, height: 844 } : { width: 1280, height: 1200 };
}

async function main() {
  if (!process.env.SENTENCE_ORDERING_PLAYWRIGHT) throw new Error("SENTENCE_ORDERING_PLAYWRIGHT must name the cached Playwright package.");
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const name of selectedCases) {
    const touch = usesTouch(name);
    const arabic = isArabic(name);
    const context = await browser.newContext({
      hasTouch: touch,
      viewport: caseViewport(name),
      reducedMotion: name === "reduced-motion-static" ? "reduce" : "no-preference",
    });
    const page = await context.newPage();
    const result = {
      name,
      transport: "isolated review mock only",
      method: touch ? "Trusted Chromium CDP touch input" : name === "keyboard-button-accessibility" || name === "arabic-keyboard-focus" || name === "reduced-motion-static" ? "Browser keyboard Enter" : "Native browser mouse input",
    };
    const cdp = touch ? await context.newCDPSession(page) : null;
    try {
      await page.goto(`http://127.0.0.1:5001/studio/sentence-ordering-review?locale=${arabic ? "ar" : "en"}&direction=${arabic ? "rtl" : "ltr"}${name === "rejection-reconciliation" ? "&reject_operation=1" : ""}`);
      await page.locator('output[data-operation-trace="[]"]').waitFor();
      if (name === "answer-key-negative") await page.waitForFunction(() => window.__LINA_SENTENCE_ORDERING_REVIEW_SCENE__ !== undefined);
      await page.evaluate(() => {
        window.sentenceOrderingEvents = [];
        for (const type of ["pointerdown", "pointerup", "pointercancel", "gotpointercapture", "lostpointercapture", "click", "keydown"]) {
          document.addEventListener(type, (event) => window.sentenceOrderingEvents.push({
            type: event.type,
            trusted: event.isTrusted,
            pointerType: event.pointerType || null,
            pointerId: event.pointerId || null,
            key: event.key || null,
            target: event.target.tagName,
          }), true);
        }
      });
      const order = () => page.locator("[data-sentence-ordering-token]").evaluateAll((nodes) => nodes.map((node) => node.dataset.sentenceOrderingToken));
      const operations = async () => JSON.parse(await page.locator("output[data-operation-trace]").getAttribute("data-operation-trace"));
      const status = () => page.locator('[role="status"]').allTextContents();
      const geometry = async () => {
        const box = await page.locator(`[data-sentence-ordering-token="${birds}"]`).boundingBox();
        const target = await page.locator(`[data-sentence-ordering-token="${clouds}"]`).boundingBox();
        assert(box && target);
        const edge = name.endsWith("edge");
        return {
          from: { x: box.x + box.width * (edge ? 0.15 : 0.5), y: box.y + box.height * 0.5 },
          to: { x: target.x + target.width * 0.5, y: target.y + target.height * 0.5 },
        };
      };
      const settle = () => page.waitForTimeout(175);
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
      if (name === "answer-key-negative") {
        result.browserScene = await page.evaluate(() => window.__LINA_SENTENCE_ORDERING_REVIEW_SCENE__);
        assert(result.browserScene, "Mounted review scene must be available for leakage inspection.");
        const catalogIds = result.browserScene.tokens.map((token) => token.id);
        const canonicalOrder = [birds, fly, over, clouds];
        assert.notDeepEqual(catalogIds, canonicalOrder);
        assert.notDeepEqual([...catalogIds].sort(), canonicalOrder);
        assert.notDeepEqual(result.browserScene.token_ids, canonicalOrder);
        assert(result.browserScene.tokens.every((token) => /^tok-[0-9a-f]{4}$/.test(token.id) && !token.id.includes(token.text.toLowerCase())));
        assert(!/birds|fly|over|clouds/i.test(`${result.browserScene.fixture_key}:${result.browserScene.fixture_version}`));
        assert(!Object.keys(result.browserScene).some((key) => /answer|accepted|valid/i.test(key)));
        result.dataAttributes = await page.evaluate(() => [...document.querySelectorAll("*")].flatMap((element) => [...element.attributes].map((attribute) => attribute.name)));
        assert(!result.dataAttributes.some((name) => /answer.*order|order.*answer|accepted.*order/i.test(name)));
      }
      await page.screenshot({ path: path.join(root, `${name}-before.png`), fullPage: true });

      if (name === "touch-cancel-retry" || name === "mouse-outside-retry") {
        const points = await geometry();
        await start(points.from);
        if (name === "touch-cancel-retry") {
          await cdp.send("Input.dispatchTouchEvent", { type: "touchCancel", touchPoints: [] });
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
      } else if (name === "keyboard-button-accessibility" || name === "arabic-keyboard-focus" || name === "reduced-motion-static") {
        const arabicKeyboard = name === "arabic-keyboard-focus";
        const controlName = arabicKeyboard ? "حرّك إلى نهاية الجملة: clouds" : arabic ? "حرّك إلى بداية الجملة: Birds" : "Move earlier: Birds";
        const expectedKeyboardReorder = arabicKeyboard
          ? { token_id: clouds, from_index: 0, to_index: 1 }
          : expectedReorder;
        const moveControl = page.getByRole("button", { name: controlName, exact: true });
        if (name === "arabic-keyboard-focus") {
          const expectedFocusOrder = [
            "حرّك إلى نهاية الجملة: clouds",
            "حرّك إلى بداية الجملة: Birds",
            "حرّك إلى نهاية الجملة: Birds",
            "حرّك إلى بداية الجملة: over",
          ];
          result.tabFocusOrder = [];
          for (const expectedName of expectedFocusOrder) {
            await page.keyboard.press("Tab");
            result.tabFocusOrder.push(await page.evaluate(() => document.activeElement?.getAttribute("aria-label")));
          }
          assert.deepEqual(result.tabFocusOrder, expectedFocusOrder);
        }
        await moveControl.focus();
        result.focus = await moveControl.evaluate((node) => ({
          focused: document.activeElement === node,
          visible: node.matches(":focus-visible"),
          outline: getComputedStyle(node).outlineStyle,
          name: node.getAttribute("aria-label"),
        }));
        assert(result.focus.focused && result.focus.visible);
        assert.equal(result.focus.name, controlName);
        await moveControl.press("Enter");
        await settle();
        if (arabicKeyboard) {
          result.focusAfter = await page.evaluate(() => ({
            name: document.activeElement?.getAttribute("aria-label"),
            visible: document.activeElement?.matches(":focus-visible"),
          }));
          assert.equal(result.focusAfter.name, controlName);
          assert(result.focusAfter.visible);
        }
        result.expectedKeyboardReorder = expectedKeyboardReorder;
      } else {
        await validDrag();
      }

      result.after = await order();
      result.operations = await operations();
      result.statusText = await status();
      assert.equal(result.operations.length, 1);
      assert.equal(result.operations[0].action_key, "REORDER_TOKEN");
      assert.deepEqual(result.operations[0].payload, result.expectedKeyboardReorder ?? expectedReorder);
      assert.equal(result.operations[0].scene_id, "review-sentence-ordering-scene");
      assert.equal(result.operations[0].base_scene_version, 2);
      if (name === "rejection-reconciliation") {
        assert.deepEqual(result.after, initialOrder);
        assert(result.statusText.some((text) => text.includes("cannot be sent")));
      } else {
        assert.deepEqual(result.after, movedOrder);
        assert(result.statusText.some((text) => text.includes(arabic ? "أُرسل" : "sent to Studio")));
      }
      assert(!result.operations.some((operation) => operation.action_key === "SUBMIT_CONFIGURATION"));

      if (name === "explicit-submit-once") {
        await page.getByRole("button", { name: "Check my sentence", exact: true }).press("Enter");
        await settle();
        result.explicitSubmit = await operations();
        assert.deepEqual(result.explicitSubmit.map((operation) => operation.action_key), ["REORDER_TOKEN", "SUBMIT_CONFIGURATION"]);
        assert.deepEqual(result.explicitSubmit[1].payload, { token_ids: movedOrder });
        assert.equal(result.explicitSubmit[1].base_scene_version, 3);
      }

      if (name === "english-ltr") {
        assert.equal(await page.locator("[data-sentence-ordering-workspace]").getAttribute("dir"), "ltr");
        assert.equal(await page.locator("[data-sentence-ordering-token-surface]").getAttribute("dir"), "ltr");
        assert(await page.getByRole("heading", { name: "Put these words into a sentence" }).isVisible());
        assert.equal(await page.getByText("Birds", { exact: true }).count(), 1);
      }
      if (name === "arabic-outer-tokens-ltr" || name === "mixed-label-layout") {
        assert.equal(await page.locator("[data-sentence-ordering-workspace]").getAttribute("dir"), "rtl");
        assert.equal(await page.locator("[data-sentence-ordering-token-surface]").getAttribute("dir"), "ltr");
        assert(await page.getByRole("heading", { name: "رتّب هذه الكلمات في جملة" }).isVisible());
        assert.equal(await page.getByText("Birds", { exact: true }).count(), 1);
        result.layout = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
        assert(result.layout.scrollWidth <= result.layout.width);
      }
      if (name === "arabic-keyboard-focus") {
        assert.equal(await page.locator("[data-sentence-ordering-workspace]").getAttribute("dir"), "rtl");
        assert.equal(await page.locator("[data-sentence-ordering-token-surface]").getAttribute("dir"), "ltr");
        assert.deepEqual(result.after, movedOrder);
        await page.getByRole("button", { name: "تحقّق من جملتي", exact: true }).press("Enter");
        await settle();
        result.explicitSubmit = await operations();
        assert.deepEqual(result.explicitSubmit.map((operation) => operation.action_key), ["REORDER_TOKEN", "SUBMIT_CONFIGURATION"]);
      }
      if (name === "narrow-mobile") {
        result.mobile = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
        assert.equal(result.mobile.width, 390);
        assert(result.mobile.scrollWidth <= result.mobile.width);
        assert.equal(await page.getByRole("button", { name: "تحقّق من جملتي", exact: true }).count(), 1);
      }
      if (name === "reduced-motion-static") {
        result.motion = await page.evaluate(() => ({
          enabled: matchMedia("(prefers-reduced-motion: reduce)").matches,
          activeAnimations: document.getAnimations().length,
          controls: [...document.querySelectorAll("button")].map((node) => ({ transition: getComputedStyle(node).transitionProperty, animation: getComputedStyle(node).animationName })),
        }));
        assert(result.motion.enabled && result.motion.activeAnimations === 0);
        assert(result.motion.controls.every((control) => control.animation === "none" && control.transition === "none"));
      }
      result.events = await page.evaluate(() => window.sentenceOrderingEvents);
      if (touch) assert(result.events.some((event) => event.trusted && event.type === "pointerdown" && event.pointerType === "touch"));
      if (name === "touch-cancel-retry") assert(result.events.some((event) => event.trusted && event.type === "pointercancel"));
      result.status = "PASS";
    } catch (error) {
      result.status = "FAIL";
      result.error = String(error);
      result.events = await page.evaluate(() => window.sentenceOrderingEvents).catch(() => []);
    }
    await page.screenshot({ path: path.join(root, `${name}-after.png`), fullPage: true });
    results.push(result);
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(root, "results.json"), JSON.stringify({
    browser: "installed Google Chrome via cached Playwright",
    transport: "isolated mock review mount only",
    coverage: "16-case STUDIO-ACT-EN-01 renderer matrix",
    results,
  }, null, 2));
  console.log(results.map((result) => ({ name: result.name, status: result.status, error: result.error, operations: result.operations?.length })));
  process.exitCode = results.every((result) => result.status === "PASS") ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
