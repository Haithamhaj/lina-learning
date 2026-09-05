const { chromium } = require(process.env.MAKE_TEN_PLAYWRIGHT);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname,process.env.MAKE_TEN_MATRIX_PHASE || 'matrix-final');
fs.mkdirSync(root,{recursive:true});
const item = 'ones-group-06';
const payload = {item_id:item,from_group_id:'ones-group',to_group_id:'ten-frame'};
const cases = ['mouse-numeral','mouse-edge','touch-numeral','touch-edge','keyboard','touch-cancel-retry','capture-loss-retry','mouse-outside-retry','touch-outside-retry','rejection','arabic-rtl-narrow-touch','reduced-motion'];
(async()=>{
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const results=[];
  for(const name of cases){
    const arabic=name==='arabic-rtl-narrow-touch';
    const touch=name.includes('touch');
    const context=await browser.newContext({hasTouch:touch,viewport:{width:arabic?390:1280,height:1200},reducedMotion:name==='reduced-motion'?'reduce':'no-preference'});
    const page=await context.newPage();
    const r={name,transport:'mock review controller',method:touch?'Trusted CDP Chromium touch emulation':name==='capture-loss-retry'?'Native mouse plus test-induced releasePointerCapture (not physical cancellation)':name==='keyboard'||name==='reduced-motion'?'Browser keyboard':'Native browser mouse'};
    const cdp=touch?await context.newCDPSession(page):null;
    try{
      await page.goto(`http://127.0.0.1:5001/studio/make-ten-review?locale=${arabic?'ar':'en'}&direction=${arabic?'rtl':'ltr'}${name==='rejection'?'&reject_operation=1':''}`);
      await page.locator('output[data-operation-trace="[]"]').waitFor();
      await page.evaluate(()=>{
        window.events=[];
        for(const type of ['pointerdown','pointerup','pointercancel','gotpointercapture','lostpointercapture','click','keydown']) document.addEventListener(type,e=>window.events.push({type:e.type,trusted:e.isTrusted,pointerType:e.pointerType,key:e.key,target:e.target.tagName,pointerId:e.pointerId}),true);
      });
      const snapshot=()=>page.locator('[data-make-ten-group]').evaluateAll(nodes=>Object.fromEntries(nodes.map(n=>[n.dataset.makeTenGroup,[...n.querySelectorAll('[data-make-ten-item]')].map(x=>x.dataset.makeTenItem)])));
      const operations=async()=>JSON.parse(await page.locator('output').getAttribute('data-operation-trace'));
      const transient=()=>page.locator('[role="status"]').first().textContent();
      const settle=()=>page.waitForTimeout(150);
      const neutral=arabic?'انقل عدادًا واحدًا من مجموعة الـ٦ إلى إطار العشرة، ثم أرسل ترتيبك للتحقق.':'Move one counter from the group of 6 into the ten-frame. Then submit what you made.';
      r.before=await snapshot();
      assert.equal(r.before['ten-frame'].length,9);assert.equal(r.before['ones-group'].length,6);
      const allBefore=Object.values(r.before).flat().sort();
      assert.equal(new Set(allBefore).size,15);
      await page.screenshot({path:path.join(root,`${name}-before.png`),fullPage:true});
      const geometry=async()=>{
        const box=await page.locator(`[data-make-ten-item="${item}"]`).boundingBox();
        const dest=await page.locator('[data-make-ten-group="ten-frame"] rect').last().boundingBox();
        return {from:{x:box.x+box.width*(name.endsWith('edge')?0.2:0.5),y:box.y+box.height/2},to:{x:dest.x+dest.width/2,y:dest.y+dest.height/2}};
      };
      const start=async(from)=>{
        if(touch)await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{...from,id:1}]});
        else {await page.mouse.move(from.x,from.y);await page.mouse.down();}
        await settle();
      };
      const move=async(from,to)=>{
        if(touch)for(let i=1;i<=15;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:from.x+(to.x-from.x)*i/15,y:from.y+(to.y-from.y)*i/15,id:1}]});
        else await page.mouse.move(to.x,to.y,{steps:15});
      };
      const end=async()=>{if(touch)await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});else await page.mouse.up();await settle();};
      const valid=async()=>{const g=await geometry();await start(g.from);await move(g.from,g.to);await end();};
      if(name.includes('retry')){
        const g=await geometry();await start(g.from);
        if(name==='touch-cancel-retry')await cdp.send('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]});
        else if(name==='capture-loss-retry'){
          // Cancellation-specific test instrumentation only; success paths use browser inputs.
          await page.evaluate(()=>{const e=window.events.findLast(x=>x.type==='pointerdown');const n=document.querySelector('[data-make-ten-item="ones-group-06"]');n.releasePointerCapture(e.pointerId);});
          await move(g.from,g.to);await end();
        }else{await move(g.from,{x:15,y:15});await end();}
        await settle();
        r.aborted={state:await snapshot(),operations:await operations(),feedback:await transient()};
        assert.deepEqual(r.aborted.state,r.before);assert.deepEqual(r.aborted.operations,[]);assert.equal(r.aborted.feedback,neutral);
        await page.screenshot({path:path.join(root,`${name}-aborted.png`),fullPage:true});
        await valid();
      }else if(name==='keyboard'||name==='reduced-motion'){
        const button=page.getByRole('button',{name:'Move to Ten frame: 6',exact:true});
        await button.focus();r.focus=await button.evaluate(n=>({focused:document.activeElement===n,visible:n.matches(':focus-visible'),shadow:getComputedStyle(n).boxShadow}));
        assert(r.focus.focused&&r.focus.visible&&r.focus.shadow!=='none');await button.press('Enter');await settle();
      }else await valid();
      r.after=await snapshot();r.operations=await operations();r.feedback=await page.locator('[role="status"]').allTextContents();
      assert.equal(r.operations.length,1);assert.equal(r.operations[0].action_key,'TRANSFER_ITEM');assert.deepEqual(r.operations[0].payload,payload);
      assert.equal(r.operations[0].base_scene_version,2);assert.equal(r.operations[0].scene_id,'review-make-ten-scene');
      assert.deepEqual(Object.values(r.after).flat().sort(),allBefore);
      assert.equal(await transient(),neutral);
      if(name==='rejection'){
        assert.deepEqual(r.after,r.before);assert(r.feedback.includes('That action cannot be sent from this saved state.'));
      }else{
        assert.deepEqual(r.after['ten-frame'],[...r.before['ten-frame'],item]);assert.deepEqual(r.after['ones-group'],r.before['ones-group'].filter(x=>x!==item));
        assert.equal(r.after['ten-frame'].length,10);assert.equal(r.after['ones-group'].length,5);
      }
      if(arabic){
        assert.equal(await page.locator('[dir]').getAttribute('dir'),'rtl');assert(await page.getByRole('heading',{name:'كوِّن عشرة'}).isVisible());
        assert.equal(await page.getByRole('button',{name:'تحقق من مجموعاتي',exact:true}).count(),1);
        r.layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));assert(r.layout.scrollWidth<=r.layout.width);
      }
      if(name==='reduced-motion'){
        r.motion=await page.evaluate(()=>({enabled:matchMedia('(prefers-reduced-motion: reduce)').matches,active:document.getAnimations().length,styles:[...document.querySelectorAll('button,svg,circle')].map(n=>({tag:n.tagName,animation:getComputedStyle(n).animationName,transition:getComputedStyle(n).transitionProperty,duration:getComputedStyle(n).transitionDuration}))}));
        assert(r.motion.enabled&&r.motion.active===0);assert(r.motion.styles.every(s=>s.animation==='none'&&(s.transition==='none'||s.duration==='0s')));
        await page.getByRole('button',{name:'Check my groups',exact:true}).press('Enter');await settle();
        r.explicitSubmit=await operations();assert.deepEqual(r.explicitSubmit.map(o=>o.action_key),['TRANSFER_ITEM','SUBMIT_CONFIGURATION']);
        assert.deepEqual(r.explicitSubmit[1].payload,{ten_frame_item_ids:r.after['ten-frame'],ones_group_item_ids:r.after['ones-group']});
        assert.equal(r.explicitSubmit[1].base_scene_version,3);assert.deepEqual(await snapshot(),r.after);
        assert(await page.getByText('Your action was sent to Studio.',{exact:true}).isVisible());
      }
      r.events=await page.evaluate(()=>window.events);
      if(touch)assert(r.events.some(e=>e.trusted&&e.type==='pointerdown'&&e.pointerType==='touch'));
      if(name==='touch-cancel-retry')assert(r.events.some(e=>e.trusted&&e.type==='pointercancel'));
      r.status='PASS';
    }catch(e){r.status='FAIL';r.error=String(e);r.events=await page.evaluate(()=>window.events).catch(()=>[]);}
    await page.screenshot({path:path.join(root,`${name}-after.png`),fullPage:true});results.push(r);await context.close();
  }
  await browser.close();fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(results,null,2));
  console.log(results.map(r=>({name:r.name,status:r.status,error:r.error,operations:r.operations?.length,counts:r.after&&Object.fromEntries(Object.entries(r.after).map(([k,v])=>[k,v.length]))})));
  process.exitCode=results.every(r=>r.status==='PASS')?0:1;
})().catch(e=>{console.error(e);process.exitCode=1;});
