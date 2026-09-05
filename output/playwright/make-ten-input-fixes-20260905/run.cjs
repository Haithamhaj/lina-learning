// Existing cached Playwright only: no package installation. Mock transport.
const { chromium } = require(process.env.MAKE_TEN_PLAYWRIGHT);
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.join(__dirname, process.env.MAKE_TEN_PHASE || 'after');
fs.mkdirSync(root,{recursive:true});
const results = [];
const expectedPayload = {item_id:'ones-group-06',from_group_id:'ones-group',to_group_id:'ten-frame'};
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  for (const name of (process.env.MAKE_TEN_CASES || 'pointer-circle-edge,pointer-visible-number-center,touch-circle-edge,keyboard-enter,reduced-motion-keyboard').split(',')) {
    const context = await browser.newContext({viewport:{width:1280,height:1200},hasTouch:name.startsWith('touch'),reducedMotion:name.startsWith('reduced')?'reduce':'no-preference'});
    const page = await context.newPage();
    const result = {name,method:name.startsWith('touch')?'Chromium CDP Input.dispatchTouchEvent, hasTouch=true':name.startsWith('pointer')?'Playwright native browser mouse input':'Playwright browser keyboard Enter',transport:'isolated review mock only'};
    try {
      await page.goto('http://127.0.0.1:5001/studio/make-ten-review?locale=en&direction=ltr');
      await page.locator('output[data-operation-trace="[]"]').waitFor();
      const counts = () => page.locator('svg[role="img"]').evaluateAll(nodes => nodes.map(node => ({label:node.getAttribute('aria-label'),count:node.querySelectorAll('circle').length})));
      result.before = await counts();
      assert.deepEqual(result.before.map(x=>x.count),[9,6]);
      await page.evaluate(() => {
        window.inputEvidence = [];
        for (const kind of ['pointerdown','pointerup','pointercancel','gotpointercapture','lostpointercapture','mousedown','mouseup','touchstart','touchend','click','keydown']) document.addEventListener(kind,event=>window.inputEvidence.push({type:event.type,trusted:event.isTrusted,pointerType:event.pointerType || null,target:event.target.tagName,key:event.key || null}),true);
      });
      await page.screenshot({path:path.join(root,`${name}-before.png`)});
      const source = await page.locator('svg').nth(1).locator('circle').last().boundingBox();
      const target = await page.locator('svg').first().locator('rect').last().boundingBox();
      const from = {x:source.x+source.width*(name.includes('center')?0.5:0.2),y:source.y+source.height/2};
      const to = {x:target.x+target.width/2,y:target.y+target.height/2};
      result.transfer = {payload:expectedPayload,from,to};
      result.hitTest = await page.evaluate(({from})=>{const n=document.elementFromPoint(from.x,from.y); const chain=[]; for(let p=n;p;p=p.parentElement)chain.push({tag:p.tagName,touchAction:getComputedStyle(p).touchAction,display:getComputedStyle(p).display}); return chain;},{from});
      if (name.startsWith('pointer')) {
        await page.mouse.move(from.x,from.y); await page.mouse.down(); await page.mouse.move(to.x,to.y,{steps:15}); await page.mouse.up();
      } else if (name.startsWith('touch')) {
        const cdp = await context.newCDPSession(page);
        await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...from,id:1}]});
        for(let i=1;i<=15;i++) await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:from.x+(to.x-from.x)*i/15,y:from.y+(to.y-from.y)*i/15,id:1}]});
        await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
      } else {
        const button = page.getByRole('button',{name:'Move to Ten frame: 6',exact:true});
        await button.focus();
        result.focus = await button.evaluate(node=>({focused:document.activeElement===node,focusVisible:node.matches(':focus-visible'),boxShadow:getComputedStyle(node).boxShadow}));
        await button.press('Enter');
      }
      await page.waitForTimeout(300);
      result.after = await counts();
      result.operations = JSON.parse(await page.locator('output').getAttribute('data-operation-trace'));
      result.inputEvents = await page.evaluate(()=>window.inputEvidence);
      result.statusText = await page.locator('[role="status"]').allTextContents();
      result.transferPassed = result.operations.length===1 && result.operations[0].action_key==='TRANSFER_ITEM' && JSON.stringify(result.operations[0].payload)===JSON.stringify(expectedPayload) && result.after[0].count===10 && result.after[1].count===5;
      if(name.startsWith('reduced')) {
        result.reducedMotion = await page.evaluate(()=>({enabled:matchMedia('(prefers-reduced-motion: reduce)').matches,styles:[...document.querySelectorAll('button,svg,circle')].map(node=>({tag:node.tagName,transitionProperty:getComputedStyle(node).transitionProperty,transitionDuration:getComputedStyle(node).transitionDuration,animationName:getComputedStyle(node).animationName})),animations:document.getAnimations().length}));
        await page.getByRole('button',{name:'Check my groups',exact:true}).press('Enter');
        await page.waitForTimeout(100);
        result.afterExplicitSubmit = JSON.parse(await page.locator('output').getAttribute('data-operation-trace'));
        result.finalStatus = await page.locator('[role="status"]').allTextContents();
        assert.equal(result.reducedMotion.enabled,true);
        assert.equal(result.reducedMotion.animations,0);
        assert(result.reducedMotion.styles.every(s=>s.animationName==='none' && (s.transitionProperty==='none' || s.transitionDuration==='0s')));
        assert.deepEqual(result.afterExplicitSubmit.map(x=>x.action_key),['TRANSFER_ITEM','SUBMIT_CONFIGURATION']);
      }
      await page.screenshot({path:path.join(root,`${name}-after.png`)});
      result.status = result.transferPassed?'PASS':'FAIL';
    } catch(error) {result.status='ERROR';result.error=String(error);}
    results.push(result);
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({browser:'installed Google Chrome via cached Playwright',results},null,2));
  console.log(results.map(r=>({name:r.name,status:r.status,before:r.before,after:r.after,operations:r.operations,error:r.error,reducedMotion:r.reducedMotion})));
  process.exitCode=results.every(r=>r.status==='PASS')?0:1;
})().catch(error=>{console.error(error);process.exitCode=1;});
