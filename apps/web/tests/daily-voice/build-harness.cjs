const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../../../..");
const out = path.resolve(process.env.DAILY_VOICE_HARNESS || "/tmp/lina-daily-voice");
fs.mkdirSync(out, { recursive: true });
const loader = path.join(out, "tsx-loader.cjs");
fs.writeFileSync(loader, `module.exports=function(source){return require(${JSON.stringify(require.resolve("sucrase"))}).transform(source,{transforms:["typescript","jsx"],jsxRuntime:"automatic",filePath:this.resourcePath}).code}`);
const webpack = require("next/dist/compiled/webpack/webpack");
webpack.init();
webpack.webpack({
  mode: "development",
  devtool: false,
  entry: path.join(__dirname, "fixture.tsx"),
  output: { path: out, filename: "bundle.js" },
  optimization: { minimize: false },
  module: { rules: [{ test: /\.tsx?$/, exclude: /node_modules/, use: loader }] },
  resolve: {
    extensions: [".tsx", ".ts", ".js"],
    modules: [path.join(root, "node_modules")],
    alias: { "@": path.join(root, "apps/web"), react: path.join(root, "node_modules/react"), "react-dom": path.join(root, "node_modules/react-dom") },
  },
}, (error, stats) => {
  if (error || stats.hasErrors()) { console.error(error || stats.toString({ all: false, errors: true })); process.exitCode = 1; return; }
  fs.writeFileSync(path.join(out, "index.html"), '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><link rel="stylesheet" href="/voice.css"><body><div id="root"></div><script src="/bundle.js"></script></body></html>');
  fs.copyFileSync(path.join(__dirname, "harness.css"), path.join(out, "voice.css"));
  console.log(out);
});
