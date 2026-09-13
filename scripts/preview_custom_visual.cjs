// Generated source runs only in the same opaque, network-disabled document as Studio.
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const { chromium } = require('playwright');
const { transform } = require('sucrase');
const { staticBridgeStateReads } = require('./custom_visual_state_reads.cjs');

// Stored values/IDs must match exactly. Numeric drawing coordinates may differ
// by at most a quarter CSS pixel after serialization, below visible resolution.
function sameReplayProjection(before, after) {
  if (before.length !== after.length) return false;
  return before.every((a, index) => {
    const b = after[index];
    if (['id','actions','value','checked','pressed'].some(key => a[key] !== b[key])) return false;
    if (JSON.stringify(a.position) !== JSON.stringify(b.position)) return false;
    if (a.bounds.some((value, i) => Math.abs(value - b.bounds[i]) > 0.25)) return false;
    return Object.keys(a.geometry).every(key => {
      const x = a.geometry[key], y = b.geometry[key];
      if (x === y) return true;
      if (!['x','y','cx','cy','r'].includes(key) || typeof x !== 'string' || typeof y !== 'string' || !x.trim() || !y.trim()) return false;
      return Number.isFinite(Number(x)) && Number.isFinite(Number(y)) &&
        Math.abs(Number(x) - Number(y)) * Math.max(a.scale, b.scale) <= 0.25;
    });
  });
}

async function preview(input) {
  const started = performance.now();
  const modulePath = path.resolve(__dirname, '../apps/web/lib/studio/custom-visual-sandbox.ts');
  const mod = new Module(modulePath, module);
  mod._compile(transform(fs.readFileSync(modulePath, 'utf8'), { transforms: ['typescript', 'imports'] }).code, modulePath);
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const timing = { launch_ms: Math.round(performance.now() - started) };
  const views = [], checks = [];
  try {
    const context = await browser.newContext({hasTouch:true});
    const page = await context.newPage();
    const touch = await page.context().newCDPSession(page);
    page.setDefaultTimeout(900);
    await page.context().route('**/*', route => route.abort());
    // A first resize/mount in another tab of the same Chrome context can
    // interfere with later pointer delivery to the original page. Replay has
    // its own context; only actual emitted state crosses into the new mount.
    const replayContext = await browser.newContext({hasTouch:true});
    await replayContext.route('**/*', route => route.abort());
    const replayPage = await replayContext.newPage();
    replayPage.setDefaultTimeout(900);
    async function mount(width, state = {}, targetPage = page) {
      const height = mod.exports.customVisualViewportHeight(width);
      await targetPage.setViewportSize({ width, height });
      await targetPage.setContent(`<html><body style="margin:0"><iframe style="width:100%;height:${height}px;border:0" sandbox="allow-scripts"></iframe></body></html>`);
      await targetPage.evaluate(doc => {
        window.previewState = null; window.previewEvents = []; window.previewError = null;
        window.onmessage = e => {
          if (e.source !== document.querySelector('iframe').contentWindow || e.data?.channel !== 'lina-full-power-canvas-v1' || e.data.nonce !== 'preview') return;
          if (e.data.type === 'EVENT') {
            if (window.previewEvents.length < 128) window.previewEvents.push(e.data);
            else window.previewState = 'EVENT_OVERFLOW';
          } else { window.previewState = e.data.type; if(e.data.type === 'ERROR')window.previewError=String(e.data.diagnostic||'Mount failed').slice(0,180); }
        };
        document.querySelector('iframe').srcdoc = doc;
      }, mod.exports.customSandboxDocument(input.source, input.parameters, 'preview', state));
      await targetPage.waitForFunction(() => window.previewState !== null, {}, { timeout: 3500 });

      return targetPage.frames().find(frame => frame !== targetPage.mainFrame());
    }
    async function replayProjection(frame) {
      return frame.locator('[data-canvas-action][data-semantic-id]').evaluateAll(elements => elements
        .filter(e=>e.getAttribute('data-canvas-action').split(/\s+/).some(a=>!['SELECT','FOCUS'].includes(a)))
        .map(e=>({id:e.getAttribute('data-semantic-id'),actions:e.getAttribute('data-canvas-action'),
          value:e.value,checked:e.checked,pressed:e.getAttribute('aria-pressed'),
          geometry:Object.fromEntries(['x','y','cx','cy','r','points','d','transform'].map(k=>[k,e.getAttribute(k)])),
          position:[e.style.left,e.style.top,e.style.transform,e.style.order],
          bounds:(()=>{const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]})(),
          scale:(()=>{const m=e instanceof SVGGraphicsElement?e.getScreenCTM():null;return m?Math.max(Math.hypot(m.a,m.b),Math.hypot(m.c,m.d)):1})()})));
    }
    async function capture(width, frame, phase, findings = []) {
      // Replay uses a second page. Bring this private preview page back to the
      // foreground and let both frame and parent paint before taking evidence.
      // DOM readiness alone can leave a newly mounted frame white in Chromium.
      await page.bringToFront();
      await frame.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      views.push({ width, phase, text: (await frame.locator('body').innerText()).slice(0, 1600), findings,
        image_url: 'data:image/png;base64,' + (await page.screenshot({ type: 'png' })).toString('base64') });
    }
    // The caller selects the current product acceptance widths. The diagnostic
    // default retains mobile coverage for sandbox regressions and historical audits.
    const widths = input.widths || [960, 320];
    if (widths.length !== 2 || new Set(widths).size !== 2 || widths.some(w => ![320, 640, 960].includes(w))) throw Error('Invalid preview widths');
    for (const width of widths) {
      const stage = performance.now();
      let frame = await mount(width);
      const findings = [];
      async function verifyMutationReplay(state, original, action, semanticId) {
        const restored = await mount(width, state, replayPage);
        const before = (await original.locator('body').innerText()).replace(/\s+/g,' ').trim();
        const after = (await restored.locator('body').innerText()).replace(/\s+/g,' ').trim();
        const geometryMatches = sameReplayProjection(await replayProjection(original), await replayProjection(restored));
        const matches = before === after && geometryMatches;
        checks.push({width,action:'STEP_REPLAY',trigger_action:action,semantic_id:semanticId,status:matches?'MATCHED':'FAILED',state:{...state},before_reload_text:before.slice(0,1600),after_reload_text:after.slice(0,1600)});
        if(!matches)findings.push(`Replay after ${action}:${semanticId} changed ${geometryMatches?'visible work text':'persisted control geometry or values'}. A later reset does not repair lost intermediate state. Read each exact emitted semantic ID before drawing.`);
      }
      if(await page.evaluate(()=>window.previewState) !== 'READY') {
        findings.push('Mount failed: '+await page.evaluate(()=>window.previewError));
        await capture(width,frame,'mount-failed',findings);continue;
      }
      const textFindings = await frame.evaluate(() => {
        const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT), parents=new Set();let n;
        while((n=walker.nextNode())&&parents.size<256)if(n.textContent.trim()&&!['STYLE','SCRIPT'].includes(n.parentElement?.tagName))parents.add(n.parentElement);
        return [...parents].flatMap(e => {
        if(!e.textContent?.trim() || !e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))return [];
        const box=e.getBoundingClientRect();if(!box.height)return []; // zero-width flex labels can still paint text beneath adjacent controls
        const style=getComputedStyle(e);let size=parseFloat(style.fontSize), distortion=1;
        if(e instanceof SVGGraphicsElement){const m=e.getScreenCTM();if(m){const x=Math.hypot(m.a,m.b),y=Math.hypot(m.c,m.d);size*=Math.min(x,y);distortion=Math.max(x,y)/Math.max(0.001,Math.min(x,y));}}
        const issues=[];
        if(distortion>1.5)issues.push({kind:'distorted',size:distortion.toFixed(1),text:e.textContent.trim().slice(0,70)});
        if(size<11.5)issues.push({kind:'small',size:size.toFixed(1),text:e.textContent.trim().slice(0,70)});
        // Visible text outside the frame is unreadable even if it is not a control.
        if(box.left < -1 || box.top < -1 || box.right > innerWidth+1 || box.bottom > innerHeight+1)
          issues.push({kind:'clipped',size:'',text:e.textContent.trim().slice(0,70)});
        // A label may be inside the viewport yet hidden beneath a sibling control.
        // Inspect direct HTML text ranges; SVG labels often intentionally ignore
        // pointer hit-testing, so their geometry remains a separate visual review.
        if(!(e instanceof SVGElement)) for(const node of e.childNodes) {
          if(node.nodeType!==Node.TEXT_NODE || !node.textContent.trim())continue;
          const range=document.createRange();range.selectNodeContents(node);
          for(const r of range.getClientRects()) {
            const hit=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);
            if(hit && hit.closest('button,input,select,[role="button"]') && !e.contains(hit) && !hit.contains(e)) {
              issues.push({kind:'covered',size:'',text:node.textContent.trim().slice(0,70)});break;
            }
          }
        }
        return issues;
      });});
      const textGroups = new Map();
      for(const issue of textFindings){const key=issue.kind+issue.size;const group=textGroups.get(key)||{...issue,count:0,examples:[]};group.count++;if(group.examples.length<3)group.examples.push(issue.text);textGroups.set(key,group);}
      findings.push(...[...textGroups.values()].slice(0,16).map(g=>
        `${g.kind==='small'?'Text smaller than 12 screen pixels ('+g.size+'px)':g.kind==='distorted'?'Text stretched by nonuniform SVG scale ('+g.size+'x)':g.kind==='covered'?'Text covered by another control':'Text outside viewport'}: ${g.count} labels; examples: ${g.examples.join(' / ')}`));
      let bindings = await frame.locator('[data-canvas-action][data-semantic-id]').evaluateAll(elements => elements.slice(0, 65).map(e => ({
        id: e.getAttribute('data-semantic-id'), actions: e.getAttribute('data-canvas-action').split(/\s+/),
        label: e.getAttribute('aria-label') || e.textContent?.slice(0, 100) || '',
        initiallyEnabled: !e.disabled && e.getAttribute('aria-disabled') !== 'true',
      })));
      if (bindings.length > 64) findings.push('Too many interaction surfaces (maximum 64).');

      const controls = await frame.locator('button,input,select,[role="button"],[data-canvas-action]').evaluateAll(elements => elements.slice(0, 96).map(e => {
        const b = e.getBoundingClientRect(), s = getComputedStyle(e);
        const visible = b.width > 0 && b.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
        return { small: visible && (b.width < 24 || b.height < 24), label: (e.getAttribute('aria-label') || e.textContent || e.tagName).slice(0, 100), visible,
          clipped: visible && (b.left < -1 || b.top < -1 || b.right > innerWidth + 1 || b.bottom > innerHeight + 1),
          keyboard: e.tabIndex >= 0 || e.disabled, bound: e.hasAttribute('data-canvas-action') };
      }));
      for (const c of controls) {
        if (c.small && c.bound) findings.push(`Interaction target smaller than 24px: ${c.label}`);
        if (c.clipped) findings.push(`Control outside viewport: ${c.label}`);
        if (c.visible && c.bound && !c.keyboard) findings.push(`Control needs keyboard access: ${c.label}`);
      }
      await capture(width, frame, 'initial', findings);
      const state = {};
      let changed = false, mutationText = null, mutationProjection = null;
      // Probe every advertised binding with real pointer/keyboard input. No geometry heuristics.
      const deferred = [], interactionFailures = new Map();
      let probes = 0;
      const interactionDeadline = performance.now() + 8000;
      let interactionBudgetExceeded = false;
      // Exercise short real workflows (for example repeated removal then submit),
      // within the original 64-control budget. Never invent a semantic event.
      for(let pass=0;pass<3 && probes<64;pass++) {
      const stateBeforePass = JSON.stringify(state);
      const occurrences = {};
      for (const binding of bindings.slice(0, 64)) {
        const key = `${binding.id}:${binding.actions.join(' ')}`;
        const index = occurrences[key] || 0; occurrences[key] = index + 1;
        for (const action of binding.actions) {
          if (performance.now() >= interactionDeadline) { interactionBudgetExceeded = true; break; }
          if(probes>=64)break;
          if(pass>0 && ['SELECT','FOCUS','SUBMIT','RESET_VIEW'].includes(action) && checks.some(c=>c.width===width&&c.semantic_id===binding.id&&c.action===action&&c.status==='OBSERVED'))continue;
          probes++;
          const failureKey=binding.id+':'+action+':'+index;
          const declaration = (input.interactions || []).find(i => i.semantic_id === binding.id && i.action === action);
          if (!declaration) { findings.push(`Undeclared control: ${action}:${binding.id}`); continue; }
          const selector = `[data-semantic-id="${binding.id}"][data-canvas-action~="${action}"]`;
          let element = frame.locator(selector).nth(index);
          const check = { width, semantic_id: binding.id, action, status: 'FAILED' };
          try {
            // Mutually exclusive actions may consume the same initial state. Probe
            // that alternative from a fresh mount, without inventing app state.
            if (!await element.isEnabled() && binding.initiallyEnabled) {
              frame = await mount(width); element = frame.locator(selector).nth(index);
              for (const key of Object.keys(state)) delete state[key]; changed = false; mutationText = null; mutationProjection = null;
            }
            if (!await element.isVisible() || !await element.isEnabled()) { check.status = 'INACTIVE'; deferred.push({selector,index,binding,action}); checks.push(check); continue; }
            // Local draft inputs need no separate semantic event: SUBMIT owns
            // their value. Supply a simple nonempty draft, not a correct answer.
            if(action==='SUBMIT') {
              const drafts=frame.locator('input:not([data-canvas-action]),textarea:not([data-canvas-action])');
              for(let j=0;j<Math.min(await drafts.count(),16);j++) {
                const draft=drafts.nth(j);
                if(!await draft.isVisible()||!await draft.isEnabled()||await draft.getAttribute('readonly')!==null)continue;
                const type=await draft.getAttribute('type');
                if(![null,'text','number'].includes(type))continue;
                if(await draft.inputValue()===''){await draft.fill('1');await draft.press('Tab');}
              }
            }
            const before = await page.evaluate(() => window.previewEvents.length);
            const kind = await element.evaluate(e => ({ tag: e.tagName.toLowerCase(), type: e.type, value: e.value, max: e.max,
              gesture: e.getAttribute('data-canvas-gesture'), target: e.getAttribute('data-canvas-drop-target') }));
            if (kind.target) {
              const targetId = kind.target;
              const box = await frame.evaluate(id => { const e = (document.getElementById(id)||document.getElementById(id.replace(/^#/,''))); if (!e) return null; const b = e.getBoundingClientRect(); return {x:b.x,y:b.y,width:b.width,height:b.height}; }, targetId);
              const b = await element.boundingBox();
              if (!box || !b) throw Error('Drop target unavailable');
              const x=b.x+b.width/2,y=b.y+b.height/2,endX=box.x+box.width/2,endY=box.y+box.height/2;
              if(width===320){await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});for(let step=1;step<=8;step++)await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+(endX-x)*step/8,y:y+(endY-y)*step/8}]});await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});}
              else{await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(endX,endY,{steps:8});await page.mouse.move(endX,endY);await page.mouse.up();}
            } else if ((kind.gesture === 'drag' && !['SELECT','FOCUS'].includes(action)) || action === 'MOVE') {
              const b = await element.boundingBox(); if (!b) throw Error('Drag target unavailable');
              const x = b.x + b.width/2, y = b.y + b.height/2;
              const endX=x+(x>width/2?-24:24), endY=y+(y>mod.exports.customVisualViewportHeight(width)/2?-24:24);
              if(width===320){
                await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
                for(let step=1;step<=4;step++)await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+(endX-x)*step/4,y:y+(endY-y)*step/4}]});
                await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
              }else{await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(endX,endY,{steps:4});await page.mouse.up();}
            } else if (kind.tag === 'input' && kind.type === 'range') {
              await element.focus(); await element.press(Number(kind.value) === Number(kind.max || 100) ? 'Home' : 'End'); await element.press('Tab');
            } else if (kind.tag === 'select') {
              const options = await element.locator('option').evaluateAll(es => es.filter(e => !e.disabled).map(e => e.value));
              await element.selectOption(options.find(value => value !== kind.value) || options[0]);
            } else if (kind.tag === 'input' && !['checkbox', 'radio', 'button', 'submit'].includes(kind.type)) {
              await element.fill(kind.type === 'number' ? String(Number(kind.value || 0) + 1) : '1'); await element.press('Tab');
            } else if(width===320) await element.tap(); else await element.click();
            await page.waitForFunction(({start,id,action}) => window.previewEvents.slice(start).some(e => e.semantic_id === id && e.semantic_action === action),
              {start:before,id:binding.id,action}, {timeout:600});
            await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
            const events = await page.evaluate(start => window.previewEvents.slice(start), before);
            const event = events.find(e => e.semantic_id === binding.id && e.semantic_action === action);
            if (!event) throw Error('No matching semantic event');
            // One gesture may emit multiple canonical updates (for example reset
            // clears a quantity and its draft). Replay all actual emitted values.
            if(events.some(e=>e.to_value!=null)) {
              for(const emitted of events)if(emitted.to_value!=null)state[emitted.semantic_id]=emitted.to_value;
              changed=true; mutationText=(await frame.locator('body').innerText()).replace(/\s+/g,' ').trim(); mutationProjection=await replayProjection(frame);
              await verifyMutationReplay(state,frame,action,binding.id);
            }
            check.status = 'OBSERVED'; check.event = event; interactionFailures.delete(failureKey);
          } catch (error) { interactionFailures.set(failureKey, `Interaction failed: ${action}:${binding.id} (${String(error.message).split('\n')[0].slice(0, 100)})`); }
          checks.push(check);
        }
      }
      if (interactionBudgetExceeded) { findings.push('Interaction verification time budget exhausted; unverified controls remain rejected.'); break; }
      if(interactionFailures.size===0 && (input.interactions||[]).every(d=>checks.some(c=>c.width===width&&c.action===d.action&&c.semantic_id===d.semantic_id&&c.status==='OBSERVED')))break;
      // Retry initially bounded/no-op controls after another real mutation. Reload
      // only actual emitted state so transient selections do not contaminate replay.
      // A repeated failed gesture cannot improve without a real intervening
      // state change. Return the existing evidence instead of spending the
      // outer process deadline and losing both screenshots and diagnostics.
      if (interactionFailures.size > 0 && JSON.stringify(state) === stateBeforePass) break;
      if(interactionFailures.size>0) frame=await mount(width,state);
      bindings=await frame.locator('[data-canvas-action][data-semantic-id]').evaluateAll(es=>es.slice(0,64).map(e=>({id:e.getAttribute('data-semantic-id'),actions:e.getAttribute('data-canvas-action').split(/\s+/),initiallyEnabled:!e.disabled&&e.getAttribute('aria-disabled')!=='true'})));
      }
      findings.push(...interactionFailures.values());
      // A submit/next control may become enabled only after earlier manipulations.
      for(const entry of deferred){
        if (performance.now() >= interactionDeadline) { findings.push('Conditional interaction verification time budget exhausted.'); break; }
        if(checks.some(c=>c.width===width&&c.action===entry.action&&c.semantic_id===entry.binding.id&&c.status==='OBSERVED'))continue;
        const element=frame.locator(entry.selector).nth(entry.index);
        if(!await element.isVisible()||!await element.isEnabled())continue;
        const before=await page.evaluate(()=>window.previewEvents.length);
        try{
          if(width===320)await element.tap();else await element.click();
          await page.waitForFunction(({start,id,action})=>window.previewEvents.slice(start).some(e=>e.semantic_id===id&&e.semantic_action===action),{start:before,id:entry.binding.id,action:entry.action},{timeout:600});
          const event=await page.evaluate(({start,id,action})=>window.previewEvents.slice(start).find(e=>e.semantic_id===id&&e.semantic_action===action),{start:before,id:entry.binding.id,action:entry.action});
          checks.push({width,semantic_id:entry.binding.id,action:entry.action,status:'OBSERVED',event});
          await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
          const emitted=await page.evaluate(start=>window.previewEvents.slice(start),before);
          if(emitted.some(e=>e.to_value!=null)){for(const e of emitted)if(e.to_value!=null)state[e.semantic_id]=e.to_value;changed=true;mutationText=(await frame.locator('body').innerText()).replace(/\s+/g,' ').trim();mutationProjection=await replayProjection(frame);await verifyMutationReplay(state,frame,entry.action,entry.binding.id);}
        }catch{findings.push(`Conditional interaction failed: ${entry.action}:${entry.binding.id}`);}
      }
      for (const declaration of input.interactions || []) {
        if (!checks.some(c => c.width === width && c.action === declaration.action && c.semantic_id === declaration.semantic_id && c.status === 'OBSERVED'))
          findings.push(`No operable semantic control: ${declaration.action}:${declaration.semantic_id}`);
      }
      const events = await page.evaluate(() => window.previewEvents);
      if (await page.evaluate(() => window.previewState) !== 'READY') findings.push('Sandbox event overflow or runtime failure.');
      // Actual post-interaction state and replay are exposed to the same model reviewer.
      const afterText = (await frame.locator('body').innerText()).slice(0, 1600);
      if (changed) {
        await capture(width, frame, 'after-interaction', []);
        const values=await frame.locator('input[data-semantic-id],select[data-semantic-id]').evaluateAll(es=>es.map(e=>({id:e.getAttribute('data-semantic-id'),value:e.value,checked:e.checked})));
        frame = await mount(width, state);
        const restored=await frame.locator('input[data-semantic-id],select[data-semantic-id]').evaluateAll(es=>es.map(e=>({id:e.getAttribute('data-semantic-id'),value:e.value,checked:e.checked})));
        if(JSON.stringify(values)!==JSON.stringify(restored))findings.push('Replay changed the values of visible controls.');
        const restoredText = await frame.locator('body').innerText();
        if(mutationProjection && !sameReplayProjection(mutationProjection,await replayProjection(frame)))
          findings.push('Replay changed persisted control selection or geometry. Restore state before constructing visible geometry.');
        if(mutationText!==null && mutationText!==restoredText.replace(/\s+/g,' ').trim())
          findings.push('Replay changed visible text from the last value-bearing action. Restore the complete observable state; SELECT/FOCUS feedback is transient.');
        const replayText = restoredText.slice(0, 1600);
        checks.push({width, action:'REPLAY', status:'RENDERED', state, before_reload_text:afterText, after_reload_text:replayText});
        await capture(width, frame, 'replay', []);
      }
      checks.push({ width, action: 'EVENT_AUDIT', events });
      timing[`${width}_ms`] = Math.round(performance.now() - stage);
    }
    const staticStarted = performance.now();
    const state_reads = staticBridgeStateReads(input.source).slice(0,128);
    timing.static_state_ms = Math.round(performance.now() - staticStarted);
    timing.total_ms = Math.round(performance.now() - started);
    return { status: views.some(v=>v.phase==='mount-failed')?'FAILED':'RENDERED', views, checks, timing, state_reads };
  } finally { await browser.close(); }
}
if (require.main === module) preview(JSON.parse(fs.readFileSync(0, 'utf8')))
  .then(result => process.stdout.write(JSON.stringify(result)))
  .catch(error => { process.stderr.write(error.message?.startsWith('CUSTOM_VISUAL_') ? error.message : 'CUSTOM_VISUAL_PREVIEW_FAILED'); process.exitCode = 1; });
module.exports = { preview, sameReplayProjection };
