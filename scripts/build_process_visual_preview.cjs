/** Local-only build of the exact production-intended view. No auth/runtime imports. */
const path=require('node:path'),fs=require('node:fs'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..');
const source=path.join(root,'apps/web/components/studio/visual-explanation');
const out=path.join(root,'output/playwright/studio-visual-process-01-v2');
fs.mkdirSync(out,{recursive:true});
const compiled=path.join(out,'compiled');
cp.execFileSync(process.execPath,[path.join(root,'node_modules/typescript/bin/tsc'),...['process-model.ts','process-view.tsx','process-review-data.ts','process-review.tsx'].map(n=>path.join(source,n)),'--outDir',compiled,'--target','es2020','--module','commonjs','--jsx','react-jsx','--esModuleInterop','--skipLibCheck','--strict'],{stdio:'inherit'});
cp.execFileSync(process.execPath,['--test',path.join(source,'process-model.test.cjs')],{stdio:'inherit',env:{...process.env,PROCESS_CHECKPOINT_COMPILED:compiled}});
const webpack=require(path.join(root,'node_modules/next/dist/compiled/webpack/webpack'));webpack.init();
webpack.webpack({mode:'production',optimization:{minimize:false},entry:path.join(compiled,'process-review.js'),output:{path:path.join(out,'site'),filename:'preview.js'},resolve:{modules:[path.join(root,'node_modules')]},devtool:false},(error,stats)=>{
 if(error||stats.hasErrors()){console.error(error||stats.toString({all:false,errors:true}));process.exitCode=1;return;}
 fs.writeFileSync(path.join(out,'site/index.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'"><link rel="icon" href="data:,"><title>Process visual checkpoint</title><div id="root"></div><script src="preview.js"></script></html>`);
 console.log('Production-mode isolated preview built. Serve site on loopback only:',path.join(out,'site'));
});
