// Isolated runtime preview. Only the production sandbox executes generated source.
const fs=require('node:fs');const path=require('node:path');const Module=require('node:module');
const {chromium}=require('playwright');const {transform}=require('sucrase');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const modulePath=path.resolve(__dirname,'../apps/web/lib/studio/custom-visual-sandbox.ts');
 const compiled=transform(fs.readFileSync(modulePath,'utf8'),{transforms:['typescript','imports']}).code;
 const mod=new Module(modulePath,module);mod._compile(compiled,modulePath);
 const {customSandboxDocument}=mod.exports;
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage();await page.route('**/*',route=>route.abort());
  const results=[];
  for(const width of [960,390]){
   await page.setViewportSize({width,height:384});
   await page.setContent('<html><body style="margin:0"><iframe style="width:100%;height:384px;border:0" sandbox="allow-scripts"></iframe></body></html>');
   await page.evaluate(doc=>{window.previewState=null;window.previewEvents=[];addEventListener('message',e=>{if(e.source===document.querySelector('iframe').contentWindow&&e.data.nonce==='preview'){if(e.data.type==='EVENT')window.previewEvents.push(e.data);else window.previewState=e.data.type;}});document.querySelector('iframe').srcdoc=doc;},customSandboxDocument(input.source,input.parameters,'preview',{}));
   await page.waitForFunction(()=>window.previewState==='READY'||window.previewState==='ERROR',{},{timeout:5000});
   if(await page.evaluate(()=>window.previewState)!=='READY')throw Error('CUSTOM_VISUAL_PREVIEW_MOUNT_FAILED');
   const f=page.frames().find(f=>f!==page.mainFrame());
   const text=(await f.locator('body').innerText()).slice(0,4000);
   const controls=await f.locator('button,input,select,[role="button"],[data-choice],[style*="cursor: pointer"],[style*="cursor:pointer"]').evaluateAll(es=>es.slice(0,32).map(e=>{const b=e.getBoundingClientRect();return {label:e.textContent||e.getAttribute('aria-label')||e.tagName,left:b.left,right:b.right,top:b.top,bottom:b.bottom,visible:b.width>0&&b.height>0&&b.left>=0&&b.top>=0&&b.right<=innerWidth&&b.bottom<=innerHeight};}));
   const findings=controls.filter(e=>!e.visible).map(e=>'Control outside viewport: '+JSON.stringify(e));
   const png=await page.screenshot({type:'png'});
   results.push({width,text,findings,image_url:'data:image/png;base64,'+png.toString('base64')});
   if(width===960){
    await f.locator('circle').evaluateAll(es=>{const point=es.find(e=>Number(e.getAttribute('r'))>=6);if(point)point.setAttribute('data-preview-probe','true');});
    const draggable=f.locator('[cursor="grab"], [style*="cursor: grab"], [style*="cursor:grab"],[data-preview-probe]').first();
    if(await draggable.count()){
     const b=await draggable.boundingBox();
     if(b&&b.width>0&&b.height>0){
      await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();
      await page.mouse.move(b.x+b.width/2+24,b.y+b.height/2-24,{steps:4});await page.mouse.up();
      const events=await page.evaluate(()=>window.previewEvents);
      const after=(await f.locator('body').innerText()).slice(0,4000);
      results.push({width,text:'Actual pointer probe: moved first draggable 24px right and 24px up. Events: '+JSON.stringify(events).slice(0,2000)+'; resulting visible state: '+after,image_url:'data:image/png;base64,'+(await page.screenshot({type:'png'})).toString('base64')});
     }
    }
   }
  }
  process.stdout.write(JSON.stringify({status:'RENDERED',views:results}));
 }finally{await browser.close();}
})().catch(()=>{process.stderr.write('CUSTOM_VISUAL_PREVIEW_FAILED');process.exitCode=1;});
