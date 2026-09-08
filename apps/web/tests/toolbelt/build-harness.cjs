// Isolated mounts of the actual adapters; no auth, student or persistence imports.
const fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '../../../..');
const out = path.resolve(process.env.CS07_HARNESS || '/tmp/lina-cs07-harness');
fs.mkdirSync(out,{recursive:true});
const loader = path.join(out,'tsx-loader.cjs');
fs.writeFileSync(loader, `module.exports=function(source){return require(${JSON.stringify(require.resolve('sucrase'))}).transform(source,{transforms:['typescript','jsx'],jsxRuntime:'automatic',filePath:this.resourcePath}).code}`);
const webpack = require('next/dist/compiled/webpack/webpack'); webpack.init();
webpack.webpack({mode:'development',devtool:false,entry:path.join(__dirname,'fixture.tsx'),output:{path:out,filename:'bundle.js'},module:{rules:[{test:/\.tsx?$/,exclude:/node_modules/,use:loader}]},resolve:{extensions:['.tsx','.ts','.js'],modules:[path.join(root,'node_modules')],alias:{'react':path.join(root,'node_modules/react'),'react-dom':path.join(root,'node_modules/react-dom')}},optimization:{minimize:false}},(error,stats)=>{
 if(error||stats.hasErrors()) {console.error(error||stats.toString({all:false,errors:true}));process.exitCode=1;return;}
 fs.cpSync(path.join(root,'apps/web/public/mathlive'),path.join(out,'mathlive'),{recursive:true});
 fs.cpSync(path.join(root,'apps/web/public/visual-toolbelt'),path.join(out,'visual-toolbelt'),{recursive:true});
 const css=path.join(root,'apps/web/lib/studio/visual-toolbelt/toolbelt.css');
 fs.writeFileSync(path.join(out,'toolbelt.css'),fs.existsSync(css)?fs.readFileSync(css):'');
 fs.writeFileSync(path.join(out,'index.html'),'<!doctype html><html lang="ar"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><link rel="stylesheet" href="/visual-toolbelt/jsxgraph.css"><link rel="stylesheet" href="/toolbelt.css"><div id="root"></div><script src="/bundle.js"></script></html>');
 console.log(out);
});
