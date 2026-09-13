// Real browser regression for the production preview, independent of live model output.
const assert = require('node:assert/strict');
const { preview, sameReplayProjection } = require('./preview_custom_visual.cjs');
const { staticBridgeStateReads } = require('./custom_visual_state_reads.cjs');
const reads = staticBridgeStateReads(`window.mount=(root,p,b)=>{const id='saved';b.read(id,0);{const id='other';b.read(id,0)}function shadow(b){b.read('ignored',0)}let dynamic='unknown';b.read(dynamic,0);b.read('literal',0)}`);
assert.deepEqual(reads.map(r=>r.semantic_id),['saved','other','literal']);
const projection={id:'point',actions:'MOVE',geometry:{cx:'40.123',cy:'50',r:'16',d:null},position:['','','',''],bounds:[24.123,34,32,32],scale:1};
assert(sameReplayProjection([projection],[{...projection,geometry:{...projection.geometry,cx:'40.12'},bounds:[24.12,34,32,32]}]));
assert(!sameReplayProjection([projection],[{...projection,geometry:{...projection.geometry,cx:'42'},bounds:[26,34,32,32]}]));
assert(!sameReplayProjection([projection],[{...projection,value:'different saved value'}]));
(async () => {
  const source = `window.mount=(root,p,b)=>{let n=b.read('amount',p.amount);const button=document.createElement('button');button.style.minWidth='32px';button.style.minHeight='32px';button.dataset.semanticId='amount';button.dataset.canvasAction='SET_VALUE';button.textContent=String(n);button.onclick=()=>{const from=String(n);n++;button.textContent=String(n);b.emit('SET_VALUE','amount',{from_value:from,to_value:String(n)});};root.appendChild(button);}`;
  const interactions = [{ action:'SET_VALUE', semantic_id:'amount', value_required:true }];
  const painted = await preview({source:source.replace("let n=", "root.style.cssText='position:fixed;inset:0;background:rgb(18,100,163)';let n="),parameters:{amount:0},interactions,widths:[960,640]});
  const imageBrowser = await require('playwright').chromium.launch({channel:'chrome',headless:true});
  try {
    const imagePage = await imageBrowser.newPage();
    const modulePath=require('node:path').resolve(__dirname,'../apps/web/lib/studio/custom-visual-sandbox.ts');
    const sandboxModule=new (require('node:module'))(modulePath,module);
    sandboxModule._compile(require('sucrase').transform(require('node:fs').readFileSync(modulePath,'utf8'),{transforms:['typescript','imports']}).code,modulePath);
    const activationPage=await imageBrowser.newPage();
    await activationPage.setContent('<iframe sandbox="allow-scripts"></iframe>');
    await activationPage.evaluate(doc=>{window.events=[];window.onmessage=e=>{if(e.data.type==='EVENT')window.events.push(e.data)};document.querySelector('iframe').srcdoc=doc},sandboxModule.exports.customSandboxDocument(`window.mount=(root,p,b)=>{root.innerHTML='<svg width="100" height="100"><circle aria-label="Point" cx="50" cy="50" r="30" /></svg><button>Native</button>';const h=b.control(root.querySelector('circle'),'point','SELECT');h.activate(()=>{throw new Error('replaced callback ran')});h.activate(()=>h.emit());const n=b.control(root.querySelector('button'),'native','SELECT');n.activate(()=>n.emit());}`,{},'activation-test',{}));
    const controls=activationPage.frameLocator('iframe');
    const point=controls.getByRole('button',{name:'Point'}),native=controls.getByRole('button',{name:'Native'});
    await point.click();await point.press('Enter');await point.press('Space');
    await native.click();await native.press('Enter');await native.press('Space');
    await activationPage.waitForFunction(()=>window.events.length>=6);
    assert.deepEqual(await activationPage.evaluate(()=>window.events.map(e=>e.semantic_id)),['point','point','point','native','native','native']);
    await point.focus();await activationPage.keyboard.down('Enter');await activationPage.keyboard.down('Enter');await activationPage.keyboard.up('Enter');
    await activationPage.waitForFunction(()=>window.events.length>=7);
    assert.equal(await activationPage.evaluate(()=>window.events.length),7);
    await activationPage.close();

    for (const view of painted.views) {
      const pixel = await imagePage.evaluate(async url => {
        const bytes=Uint8Array.from(atob(url.split(',')[1]),c=>c.charCodeAt(0));
        const bitmap=await createImageBitmap(new Blob([bytes],{type:'image/png'}));
        const canvas=new OffscreenCanvas(bitmap.width,bitmap.height),ctx=canvas.getContext('2d');
        ctx.drawImage(bitmap,0,0);return [...ctx.getImageData(100,100,1,1).data];
      }, view.image_url);
      assert.deepEqual(pixel,[18,100,163,255],`${view.width} ${view.phase} must contain painted content`);
    }
    assert.equal(painted.views.length,6);
  } finally { await imageBrowser.close(); }
  const good = await preview({source,parameters:{amount:0},interactions});
  const bottomControls = await preview({source:`window.mount=(root,p,b)=>{const top=document.createElement('button'),bottom=document.createElement('button');top.style.cssText='position:absolute;left:140px;top:275px;width:80px;height:30px';bottom.style.cssText='position:absolute;left:140px;top:320px;width:80px;height:30px';root.append(top,bottom);const a=b.control(top,'amount','SET_VALUE'),c=b.control(bottom,'choice','SELECT');let n=a.read(0);top.textContent=String(n);bottom.textContent='Select';top.onclick=()=>{n++;a.emit(n);top.textContent=String(n)};bottom.onclick=()=>c.emit()}`,parameters:{},interactions:[...interactions,{semantic_id:'choice',action:'SELECT',value_required:false}],widths:[960,640]});
  assert.deepEqual(bottomControls.views.flatMap(v=>v.findings),[]);
  assert.equal(bottomControls.checks.filter(c=>c.action==='SELECT'&&c.status==='OBSERVED').length,2);
  assert.equal(good.views.length, 6);
  assert.deepEqual(good.views.flatMap(v => v.findings), []);
  assert.equal(good.checks.filter(c => c.status==='OBSERVED').length, 2);
  for(const replay of good.checks.filter(c=>c.action==='REPLAY')) {
    assert.equal(replay.before_reload_text, '1'); assert.equal(replay.after_reload_text, '1');
  }
  const dead = await preview({source:source.replace("b.emit('SET_VALUE','amount',{from_value:from,to_value:String(n)});",''),parameters:{amount:0},interactions});
  assert(dead.views.flatMap(v=>v.findings).some(x=>x.includes('No operable semantic control')));
  const missing = await preview({source:'window.mount=root=>{root.textContent="rendered only"}',parameters:{},interactions});
  assert(missing.views.flatMap(v=>v.findings).some(x=>x.includes('No operable semantic control')));
  const handles = await preview({source: `window.mount=(root,p,b)=>{const e=document.createElement('button');e.style.minWidth='40px';e.style.minHeight='40px';const h=b.control(e,'amount','SET_VALUE');const render=()=>e.textContent=String(h.read(p.amount));e.onclick=()=>{h.emit(h.read(p.amount)+1);render()};root.appendChild(e);render()}`,parameters:{amount:0},interactions});
  assert.deepEqual(handles.views.flatMap(v=>v.findings), []);
  for(const replay of handles.checks.filter(c=>c.action==='REPLAY')) assert.equal(replay.before_reload_text, replay.after_reload_text);
  const identity = await preview({source: `window.mount=(root,p,b)=>{const e=document.createElement('button');e.style.minWidth='40px';e.style.minHeight='40px';const h=b.control(e,'choice','SELECT');e.textContent='Choose';e.onclick=()=>{h.emit('untrusted-extra-value');e.textContent=h.selected?'Selected':'Choose'};root.appendChild(e)}`, parameters:{}, interactions:[{action:'SELECT',semantic_id:'choice',value_required:false}]});
  for(const check of identity.checks.filter(c=>c.status==='OBSERVED')) assert.equal(check.event.to_value,null);
  const drag = await preview({source: `window.mount=(root,p,b)=>{let pos=b.read('point',{x:40,y:40});function render(){root.innerHTML='';const e=document.createElement('button');e.textContent='Move';e.style.cssText='position:absolute;width:48px;height:32px;transform:translate(-50%,-50%);left:'+pos.x+'px;top:'+pos.y+'px';root.appendChild(e);const h=b.control(e,'point','MOVE');h.drag({move:q=>{pos={x:q.clientX,y:q.clientY};render()},end:()=>pos});}render()}`,parameters:{},interactions:[{action:'MOVE',semantic_id:'point',value_required:true}]});
  assert.deepEqual(drag.views.flatMap(v=>v.findings), []);
  for(const check of drag.checks.filter(c=>c.status==='OBSERVED'))assert.deepEqual(JSON.parse(check.event.to_value),{x:64,y:64});
  const explicitDrag = await preview({source:`window.mount=(root,p,b)=>{const e=document.createElement('button');e.textContent='Move';e.style.cssText='width:48px;height:32px';root.appendChild(e);const h=b.control(e,'point','MOVE');h.drag({end:()=>{h.emit('moved');return 'moved'}})}`,parameters:{},interactions:[{action:'MOVE',semantic_id:'point',value_required:true}]});
  for(const audit of explicitDrag.checks.filter(c=>c.action==='EVENT_AUDIT'))assert.equal(audit.events.length,1);
  const reset = await preview({source:`window.mount=(root,p,b)=>{let n=b.read('amount',0);const e=document.createElement('button'),r=document.createElement('button');for(const c of [e,r]){c.style.cssText='min-width:40px;min-height:40px';root.appendChild(c)}const h=b.control(e,'amount','SET_VALUE'),hr=b.control(r,'reset','RESET_VIEW');const render=()=>e.textContent='Amount '+n;r.textContent='Reset';e.onclick=()=>{n++;h.emit(n);render()};r.onclick=()=>{n=0;hr.emit();h.emit(n);render()};render()}`,parameters:{},interactions:[...interactions,{action:'RESET_VIEW',semantic_id:'reset',value_required:false}]});
  assert.deepEqual(reset.views.flatMap(v=>v.findings),[]);
  for(const check of reset.checks.filter(c=>c.action==='REPLAY'))assert.equal(check.state.amount,'0');
  const resetMasksLoss = await preview({source:`window.mount=(root,p,b)=>{let n=0;const e=document.createElement('button'),r=document.createElement('button');for(const c of [e,r]){c.style.cssText='width:90px;height:40px';root.appendChild(c)}const h=b.control(e,'amount','SET_VALUE'),hr=b.control(r,'reset','RESET_VIEW');const render=()=>e.textContent='Amount '+n;r.textContent='Reset';e.onclick=()=>{n++;h.emit(n);render()};r.onclick=()=>{n=0;hr.emit();h.emit(0);render()};render()}`,parameters:{},interactions:[...interactions,{action:'RESET_VIEW',semantic_id:'reset',value_required:false}]});
  assert(resetMasksLoss.views.some(v=>v.findings.some(f=>f.includes('Replay after SET_VALUE:amount'))));
  const workflow = await preview({source:`window.mount=(root,p,b)=>{let n=b.read('remove',0),answer=b.read('submit','');const remove=document.createElement('button'),input=document.createElement('input'),submit=document.createElement('button');for(const e of [remove,input,submit]){e.style.cssText='min-width:40px;min-height:40px';root.appendChild(e)}const hr=b.control(remove,'remove','SET_VALUE'),hs=b.control(submit,'submit','SUBMIT');remove.textContent='Remove';submit.textContent='Submit';input.type='number';input.value=answer;function render(){remove.disabled=n>=2;input.style.display=submit.style.display=n>=2?'inline-block':'none'}remove.onclick=()=>{n++;hr.emit(n);render()};submit.onclick=()=>{if(input.value)hs.emit(input.value)};render()}`,parameters:{},interactions:[{action:'SET_VALUE',semantic_id:'remove',value_required:true},{action:'SUBMIT',semantic_id:'submit',value_required:true}]});
  assert.deepEqual(workflow.views.flatMap(v=>v.findings),[]);
  assert.equal(workflow.checks.filter(c=>c.action==='SUBMIT'&&c.status==='OBSERVED').length,2);
  const lostReplay = await preview({source:`window.mount=(root,p,b)=>{let n=0;const e=document.createElement('button');e.style.cssText='min-width:40px;min-height:40px';root.appendChild(e);const h=b.control(e,'amount','SET_VALUE');h.read(0);e.textContent='Amount '+n;e.onclick=()=>{n++;e.textContent='Amount '+n;h.emit(n)}}`,parameters:{},interactions});
  assert(lostReplay.views.some(v=>v.findings.some(f=>f.includes('Replay changed visible text'))));
  const geometry = await preview({source:`window.mount=(root,p,b)=>{let x=40;const e=document.createElement('button');e.textContent='Move';e.style.cssText='position:absolute;top:40px;left:'+x+'px;width:48px;height:32px';root.appendChild(e);const h=b.control(e,'point','MOVE');x=h.read(40);h.drag({move:q=>{x=q.clientX;e.style.left=x+'px'},end:()=>x})}`,parameters:{},interactions:[{action:'MOVE',semantic_id:'point',value_required:true}]});
  assert(geometry.views.some(v=>v.findings.some(f=>f.includes('Replay changed persisted control'))));
  const covered = await preview({source:`window.mount=root=>{root.innerHTML='<span style="position:absolute;left:10px;top:10px">Hidden label</span><button style="position:absolute;left:10px;top:10px;width:150px;height:40px">Cover</button>'}`,parameters:{},interactions:[]});
  assert(covered.views.some(v=>v.findings.some(f=>f.includes('Text covered by another control'))));
  const collapsed = await preview({source:`window.mount=root=>{root.innerHTML='<div style="display:flex;width:130px"><span style="flex:1;min-width:0">Material</span><button style="width:130px;flex:none;height:40px">Choose</button></div>'}`,parameters:{},interactions:[]});
  assert(collapsed.views.some(v=>v.findings.some(f=>f.includes('Text covered by another control'))));
  const boundedButtons=await preview({source:`window.mount=(root,p,b)=>{let n=b.read('amount',0);const down=document.createElement('button'),up=document.createElement('button');for(const e of [down,up]){e.style.cssText='width:100px;height:40px';root.appendChild(e)}const hd=b.control(down,'amount','SET_VALUE'),hu=b.control(up,'amount','SET_VALUE');const render=()=>{down.textContent='Down '+n;up.textContent='Up '+n};down.onclick=()=>{if(n>0){n--;hd.emit(n);render()}};up.onclick=()=>{n++;hu.emit(n);render()};render()}`,parameters:{},interactions});
  assert.deepEqual(boundedButtons.views.flatMap(v=>v.findings),[]);
  const squashedText = await preview({source:`window.mount=root=>{root.innerHTML='<svg width="100%" height="100%" viewBox="0 0 960 200" preserveAspectRatio="none"><text x="30" y="40" font-size="18">Readable in both dimensions</text></svg>'}`,parameters:{},interactions:[]});
  assert(squashedText.views.some(v=>v.width===320&&v.findings.some(f=>f.includes('Text smaller than 12 screen pixels'))));
  assert(squashedText.views.some(v=>v.width===320&&v.findings.some(f=>f.includes('nonuniform SVG scale'))));
  const manyDead = await preview({source:`window.mount=(root,p,b)=>{for(let i=0;i<20;i++){const e=document.createElement('button');e.textContent='Try '+i;e.style.cssText='width:50px;height:30px';root.appendChild(e);b.control(e,'attempt','SET_VALUE')}}`,parameters:{},interactions:[{action:'SET_VALUE',semantic_id:'attempt',value_required:true}]});
  assert(manyDead.views.some(v=>v.width===960) && manyDead.views.some(v=>v.width===320));
  assert(manyDead.views.some(v=>v.findings.some(f=>f.includes('time budget exhausted'))));
  const desktop = await preview({source:`window.mount=root=>{root.textContent='Desktop preview';root.style.fontSize='16px'}`,parameters:{},interactions:[],widths:[960,640]});
  assert.deepEqual(desktop.views.map(v=>v.width),[960,640]);
  assert.deepEqual(desktop.views.flatMap(v=>v.findings),[]);
  const broken = await preview({source:`window.mount=()=>{throw new TypeError('data.map is not a function')}`,parameters:{},interactions:[]});
  assert.equal(broken.status,'FAILED');assert.equal(broken.views.length,2);assert(broken.views.every(v=>v.findings[0].includes('data.map')));
  console.log(JSON.stringify({status:'PASSED',checks:['real click','semantic event','zero parameter','wide/narrow replay','dead interaction rejected','unbound interaction rejected','touch drag survives redraw','mount diagnostic','discarded state rejected','late geometry restoration rejected','multi-step local draft submission','coupled reset events replayed','intermediate replay before reset','covered and collapsed labels rejected']}));
})().catch(error=>{console.error(error);process.exitCode=1});
