// NODE_PATH may point to an existing Playwright runtime. Serve build-harness.cjs output on loopback.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[], badAssets=[], results=[];
 await page.addInitScript(() => {
   const NativeObserver = window.ResizeObserver;
   const active = new Map();
   window.observerCount = () => active.size;
   window.ResizeObserver = class extends NativeObserver {
     observe(element, options) { if (!active.has(this)) active.set(this, new Set()); active.get(this).add(element); super.observe(element, options); }
     unobserve(element) { const targets = active.get(this); targets?.delete(element); if (!targets?.size) active.delete(this); super.unobserve(element); }
     disconnect() { active.delete(this); super.disconnect(); }
   };
 });
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400) badAssets.push(r.url());});
 const state=async()=>JSON.parse(await page.locator('#semantic-result').textContent());
 const settle=()=>page.waitForFunction(()=>window.engineCounts?.().boards===1 && window.engineCounts?.().stages===1 && document.querySelector('math-field'));
 const load=async()=>{await page.goto(process.env.CS07_URL||'http://127.0.0.1:5077');await settle();};
 const check=async(name,fn)=>{try{await load();await fn();results.push({name,pass:true});console.log('PASS',name);}catch(e){results.push({name,pass:false,error:e.message});console.log('FAIL',name,e.message);}};
 const drag=async(selector,start,end,touch=false)=>{
   const surface=page.locator(selector);await surface.scrollIntoViewIfNeeded();const box=await surface.boundingBox();
   const a={x:box.x+box.width*start[0],y:box.y+box.height*start[1]},b={x:box.x+box.width*end[0],y:box.y+box.height*end[1]};
   if(touch){const cdp=await page.context().newCDPSession(page);await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...a,id:1}]});for(let i=1;i<=8;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:a.x+(b.x-a.x)*i/8,y:a.y+(b.y-a.y)*i/8,id:1}]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await cdp.detach();}
   else {await page.mouse.move(a.x,a.y);await page.mouse.down();await page.mouse.move(b.x,b.y,{steps:10});await page.mouse.up();}
 };
 await check('Motion retargets mid-transition and settles without an infinite loop',async()=>{
   assert.equal(await page.getByRole('button',{name:'Focus target',exact:true}).count(),1);
   await page.getByRole('button',{name:'Focus target',exact:true}).click();
   await page.getByRole('button',{name:'Focus source',exact:true}).click();
   await page.getByRole('button',{name:'Focus target',exact:true}).click();
   const ring=page.locator('[data-engine="motion"] circle[fill="none"]');
   await page.waitForFunction(()=>Number(document.querySelector('[data-engine="motion"] circle[fill="none"]').getAttribute('cx'))===270);
   await page.waitForTimeout(500);assert.equal(Number(await ring.getAttribute('cx')),270);assert.equal((await state()).focus,'target');
 });
 await check('Motion reduced-motion equivalent is immediate and retains semantic focus',async()=>{
   await page.emulateMedia({reducedMotion:'reduce'});await load();
   await page.getByRole('button',{name:'Focus target',exact:true}).press('Enter');
   await page.waitForTimeout(40);assert.equal(Number(await page.locator('[data-engine="motion"] circle[fill="none"]').getAttribute('cx')),270);
   await page.emulateMedia({reducedMotion:'no-preference'});
 });
 await check('Konva keyboard placement and reset return stable IDs',async()=>{
   const button=page.getByRole('button',{name:'Place A in B',exact:true});assert.equal(await button.count(),1);await button.focus();await page.keyboard.press('Enter');
   assert.deepEqual((await state()).placement,{objectId:'object-a',targetId:'target-b'});
   assert.notEqual(await button.evaluate(el=>getComputedStyle(el).outlineStyle),'none');
   await page.getByRole('button',{name:'Return A',exact:true}).press('Space');assert.equal((await state()).placement.targetId,null);
 });
 await check('Konva object label follows the object during dragging',async()=>{
   const surface=page.locator('[data-engine="konva"] .toolbelt-surface');await surface.scrollIntoViewIfNeeded();const box=await surface.boundingBox();
   await page.mouse.move(box.x+box.width*70/320,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width*.5,box.y+box.height/2,{steps:8});
   const positions=await page.evaluate(()=>window.spatialPositions());await page.mouse.up();assert.ok(Math.abs(positions.circle.x-positions.label.x)<15, 'Label detached from dragged object');
 });
 for(const touch of [false,true]) await check(`Konva ${touch?'touch':'pointer'} drag returns semantic placement after narrow resize`,async()=>{
   await page.setViewportSize({width:320,height:844});
   await drag('[data-engine="konva"] .toolbelt-surface',[70/320,.5],[252/320,.5],touch);
   assert.deepEqual((await state()).placement,{objectId:'object-a',targetId:'target-b'});
   await drag('[data-engine="konva"] .toolbelt-surface',[252/320,.5],[100/320,.5],touch);
   assert.equal((await state()).placement.targetId,null);await page.setViewportSize({width:390,height:844});
 });
 await check('JSXGraph resize preserves CSS-owned width without a shrinking feedback loop',async()=>{
   const before=await page.locator('.jxgbox').boundingBox();await page.waitForTimeout(600);const after=await page.locator('.jxgbox').boundingBox();
   assert.ok(Math.abs(before.width-after.width)<2, `Board shrank from ${before.width} to ${after.width}`);
   assert.ok(after.width>250);
 });
 await check('JSXGraph exact keyboard state and external control preserve LTR coordinates',async()=>{
   assert.equal(await page.getByRole('spinbutton',{name:'X coordinate',exact:true}).count(),1);
   await page.getByRole('spinbutton',{name:'X coordinate',exact:true}).fill('-2');
   assert.deepEqual((await state()).point,{x:-2,y:1});
   await page.getByRole('spinbutton',{name:'Y coordinate',exact:true}).fill('99');assert.deepEqual((await state()).point,{x:-2,y:4});
   assert.equal(await page.locator('.jxgbox').evaluate(el=>getComputedStyle(el).direction),'ltr');
   await page.getByRole('button',{name:'External reset',exact:true}).click();assert.deepEqual((await state()).point,{x:-3,y:2});
 });
 await check('JSXGraph native point keyboard movement also hands off exact semantic state',async()=>{
   await page.locator('.jxgbox ellipse:visible').focus();await page.keyboard.press('ArrowRight');assert.deepEqual((await state()).point,{x:3,y:1});
 });
 for(const touch of [false,true]) await check(`JSXGraph ${touch?'touch':'pointer'} construction snaps to exact integers`,async()=>{
   await drag('.jxgbox',[.7,.4],[.32,.69],touch);assert.deepEqual((await state()).point,{x:-2,y:-2});
 });
 await check('MathLive follows external application value without remount or stale callback',async()=>{
   await page.locator('math-field').evaluate(el=>el.dataset.identity='same');
   await page.getByRole('button',{name:'External reset',exact:true}).click();
   assert.equal(await page.locator('math-field').evaluate(el=>el.value),'\\frac{1}{2}');assert.equal(await page.locator('math-field').getAttribute('data-identity'),'same');
   await page.locator('math-field').click();await page.waitForFunction(()=>document.activeElement===document.querySelector('math-field'));await page.keyboard.press('End');await page.keyboard.type('+1');
   await page.waitForFunction(()=>JSON.parse(document.querySelector('#semantic-result').textContent).math.endsWith('+1'));assert.equal((await state()).math,'\\frac{1}{2}+1');assert.equal((await state()).submission,null);
   await page.getByRole('button',{name:'Submit expression',exact:true}).click();assert.deepEqual((await state()).submission,{format:'latex',value:'\\frac{1}{2}+1'});
 });
 await check('Application rejection reconciles engine state',async()=>{
   await page.getByRole('checkbox',{name:'Reject edits'}).check();
   await page.locator('math-field').click();await page.waitForFunction(()=>document.activeElement===document.querySelector('math-field'));await page.keyboard.press('End');await page.keyboard.type('+9');await page.waitForTimeout(100);
   assert.equal(await page.locator('math-field').evaluate(el=>el.value),'\\frac{3}{4}');
   await drag('[data-engine="konva"] .toolbelt-surface',[70/320,.5],[252/320,.5]);assert.equal((await state()).placement.targetId,null);
   await drag('.jxgbox',[.7,.4],[.3,.7]);assert.deepEqual((await state()).point,{x:2,y:1});
 });
 await check('MathLive virtual-keyboard touch input reaches application state',async()=>{
   const touchPage=await browser.newPage({hasTouch:true,viewport:{width:390,height:844}});
   try {
     await touchPage.goto(process.env.CS07_URL||'http://127.0.0.1:5077');await touchPage.locator('math-field').waitFor();
     await touchPage.locator('math-field').tap();await touchPage.waitForFunction(()=>document.activeElement===document.querySelector('math-field'));
     if(!await touchPage.evaluate(()=>window.mathVirtualKeyboard.visible)) await touchPage.locator('math-field [part="virtual-keyboard-toggle"]').tap();
     await touchPage.locator('.ML__keyboard .MLK__keycap[aria-label="7"]:visible').tap();
     await touchPage.waitForFunction(()=>JSON.parse(document.querySelector('#semantic-result').textContent).math.includes('7'));
     const result=JSON.parse(await touchPage.locator('#semantic-result').textContent());assert.equal(result.math,await touchPage.locator('math-field').evaluate(el=>el.value));assert.match(result.math,/7/);assert.equal(result.submission,null);
     fs.mkdirSync('/tmp/lina-cs07-evidence',{recursive:true});await touchPage.screenshot({path:'/tmp/lina-cs07-evidence/touch-keyboard.png'});
   } finally {await touchPage.close();}
 });
 await check('MathLive validates empty submit without inventing grading',async()=>{
   await page.locator('math-field').click();await page.waitForFunction(()=>document.activeElement===document.querySelector('math-field'));await page.locator('math-field').evaluate(el=>el.select());await page.keyboard.press('Backspace');await page.waitForFunction(()=>JSON.parse(document.querySelector('#semantic-result').textContent).math==='');
   await page.getByRole('button',{name:'Submit expression',exact:true}).click();assert.equal((await state()).submission,null);
   assert.match(await page.locator('[data-engine="mathlive"] output').textContent(),/1–200/);
 });
 await check('Repeated unmount frees boards, stages and math fields; remount restores application values',async()=>{
   await page.getByRole('button',{name:'External reset',exact:true}).click();
   for(let i=0;i<4;i++){
     await page.locator('math-field').evaluate(el=>window.retiredMathField=el);
     await page.getByRole('button',{name:'Toggle mounts',exact:true}).click();
     assert.deepEqual(await page.evaluate(()=>window.engineCounts()),{stages:0,boards:0});assert.equal(await page.evaluate(()=>window.observerCount()),0);
     await page.evaluate(()=>{window.retiredMathField.value='99';window.retiredMathField.dispatchEvent(new Event('input'));});assert.equal((await state()).math,'\\frac{1}{2}');assert.equal(await page.locator('math-field').count(),0);
     await page.getByRole('button',{name:'Toggle mounts',exact:true}).click();await settle();
     assert.equal(await page.locator('math-field').evaluate(el=>el.value),'\\frac{1}{2}');
   }
 });
 await check('Unmount during MathLive lazy loading does not create a late field',async()=>{
   let requested=false;
   await page.route('**/*mathlive_mjs.bundle.js',async route=>{requested=true;await new Promise(resolve=>setTimeout(resolve,250));await route.continue();});
   await page.reload();await page.waitForSelector('[data-engine="mathlive"]');
   assert.equal(requested,true);await page.getByRole('button',{name:'Toggle mounts',exact:true}).click();await page.waitForTimeout(400);
   assert.equal(await page.locator('math-field').count(),0);assert.deepEqual(await page.evaluate(()=>window.engineCounts()),{stages:0,boards:0});assert.equal(await page.evaluate(()=>window.observerCount()),0);
   await page.unroute('**/*mathlive_mjs.bundle.js');
 });
 await check('Narrow and wide Arabic/English layouts resize without horizontal overflow',async()=>{
   for(const width of [320,768,1280]){await page.setViewportSize({width,height:900});await page.waitForTimeout(100);
     assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
     const size=await page.locator('.jxgbox').boundingBox();assert.ok(Math.abs(size.width-size.height)<3);
     const surface=await page.locator('[data-engine="konva"] .toolbelt-surface').boundingBox();const canvas=await page.locator('[data-engine="konva"] canvas').boundingBox();assert.ok(Math.abs(surface.width-canvas.width)<2);
   }
   fs.mkdirSync('/tmp/lina-cs07-evidence',{recursive:true});await page.screenshot({path:'/tmp/lina-cs07-evidence/wide.png',fullPage:true});
   await page.setViewportSize({width:390,height:844});await page.screenshot({path:'/tmp/lina-cs07-evidence/narrow.png',fullPage:true});
 });
 await browser.close();
 fs.mkdirSync('/tmp/lina-cs07-evidence',{recursive:true});fs.writeFileSync('/tmp/lina-cs07-evidence/results.json',JSON.stringify({results,errors,badAssets},null,2));
 assert.deepEqual(errors,[]);assert.deepEqual(badAssets,[]);assert.equal(results.filter(r=>!r.pass).length,0);
})().catch(e=>{console.error(e);process.exitCode=1});
