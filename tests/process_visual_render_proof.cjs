// Test-only adapter: accepted server seed/state -> unchanged production-intended ProcessView.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const ts=require('typescript'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const source=path.resolve(__dirname,'../apps/web/components/studio/visual-explanation');
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const filename=path.join(source,name+'.'+(name==='process-view'?'tsx':'ts'));
 const code=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText;
 const module={exports:{}};new Function('require','module','exports',code)(id=>id.startsWith('./')?load(id.slice(2)):require(id),module,module.exports);return cache[name]=module.exports;
}
const {seed,state}=JSON.parse(fs.readFileSync(0,'utf8'));
assert.deepEqual(seed,load('process-review-data').processReviewScenes[1]);
const {ProcessView}=load('process-view');
const html=renderToStaticMarkup(React.createElement(ProcessView,{scene:seed,state:{selectedId:state.selected_stage_id,focusedStageId:state.focused_stage_id,revealedIds:state.revealed_stage_ids,highlightedStageIds:[state.focused_stage_id],highlightedRelationIds:state.highlighted_relation_ids,activeExplanationStageId:state.active_explanation_stage_id,tracingRelationId:null},onAction:()=>{},onExplain:()=>{}}));
for(const stage of seed.stages)assert.ok(html.includes('data-stage="'+stage.id+'"'));
for(const relation of seed.relations)assert.ok(html.includes('data-relation="'+relation.id+'"'));
assert.ok(html.includes('Stage 3 of 4'));assert.ok(html.includes('The butterfly develops inside the pupa.'));
process.stdout.write(JSON.stringify({renderer:'unchanged ProcessView',objects:seed.stages.map(s=>s.id),relations:seed.relations.map(r=>r.id),focus:state.focused_stage_id,ordinal:'Stage 3 of 4',htmlCharacters:html.length}));
