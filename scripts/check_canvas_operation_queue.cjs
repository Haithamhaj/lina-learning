const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path'), http = require('node:http');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
(async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'lina-canvas-queue-'));
  execFileSync(process.execPath,['apps/web/tests/canvas-visual-intelligence/build-harness.cjs'],{env:{...process.env,CANVAS_QUEUE_FIXTURE:'1',CANVAS_VISUAL_HARNESS:dir}});
  const server=http.createServer((req,res)=>{const name=req.url.split('?')[0]==='/'?'index.html':req.url.slice(1).split('?')[0];if(!['index.html','bundle.js'].includes(name)){res.writeHead(404).end();return;}res.setHeader('content-type',name.endsWith('.js')?'application/javascript':'text/html');res.end(fs.readFileSync(path.join(dir,name)));});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try{
    const page=await browser.newPage();
    for(const reject of [false,true]){
      await page.goto(`http://127.0.0.1:${server.address().port}/${reject?'?reject':''}`);
      const button=page.frameLocator('iframe').getByRole('button');await button.waitFor();
      assert.equal(await page.locator('[data-build-loads]').innerText(),'1');
      const frame=page.locator('iframe');
      assert.equal(await frame.getAttribute('sandbox'),'allow-scripts');
      assert.equal(await frame.getAttribute('referrerpolicy'),'no-referrer');
      // Actual rapid browser actions, while the host waits on the first save.
      await button.click();await button.click();await button.click();
      if(reject){await page.getByRole('alert').waitFor();await page.waitForTimeout(250);assert.equal(await page.locator('[data-calls]').innerText(),'1');assert.equal(await page.locator('[data-saved]').innerText(),'0');}
      else{await page.waitForFunction(()=>document.querySelector('[data-saved]').textContent==='3');assert.equal(await page.locator('[data-calls]').innerText(),'3');assert.equal(await page.locator('[data-failure]').innerText(),'');}
    }
    console.log('PASSED: rapid mutations serialize against committed versions; rejection cancels queued work.');
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve));fs.rmSync(dir,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1});
