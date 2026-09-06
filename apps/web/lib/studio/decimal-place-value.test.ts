import test from 'node:test';
import assert from 'node:assert/strict';
import {parsePlaceResult,readPlaceValueState,readPlaceValueSnapshot,placeWeights} from './decimal-place-value';
import {resolveApprovedStudioRenderer} from './renderer-host';

test('numeric entry is exact and rejects incomplete/excess-precision strings',()=>{
  for(const [text,value] of [['1.2',120],['1.20',120],['٢٫١٢',212],['0',0]] as const)assert.equal(parsePlaceResult(text),value);
  for(const text of ['', '1.', '1.001','200','1e2','01',' 1','.5'])assert.equal(parsePlaceResult(text),null);
});
test('unknown and malformed seeds fail closed',()=>{
  for(const value of [null,{}, {source_ref:'decimal-place:v1:unknown'}])assert.equal(readPlaceValueState(value),null);
});
const zero=()=>({hundreds:0,tens:0,ones:0,tenths:0,hundredths:0});
export const validState=()=>({source_ref:'decimal-place:v1:add-carry',catalog_version:'decimal-place-value-catalog-v1',mode:'ADD',operands:[{id:'a',value:127,text:'1.27'},{id:'b',value:85,text:'0.85'}],places:Object.entries(placeWeights).map(([id,weight])=>({id,weight})),pools:{a:{...zero(),ones:1,tenths:2,hundredths:7},b:{...zero(),tenths:8,hundredths:5},result:zero()},result:null});
test('Host projection never repairs a present malformed attempt from seed defaults',()=>{
  const seed=validState();const snapshot=(attempt:unknown)=>({active_scene_seed:seed,state_payload:{decimal_place_value:attempt},active_scene_contract:{scene_version:3}});
  for(const attempt of [null,[],{}, {result:212},{pools:seed.pools}, {pools:seed.pools,result:null,mode:'SUBTRACT'}])assert.equal(readPlaceValueSnapshot(snapshot(attempt)),null);
  assert.ok(readPlaceValueSnapshot(snapshot({pools:seed.pools,result:null})));
  assert.ok(readPlaceValueSnapshot({active_scene_seed:seed,state_payload:{},active_scene_contract:{scene_version:2}}));
  assert.equal(readPlaceValueSnapshot({active_scene_seed:seed,state_payload:{},active_scene_contract:{scene_version:3}}),null);
});
test('Host projection validates immutable initial seed before current pools can mask corruption',()=>{
  const seed:any=validState();const attempt={pools:structuredClone(seed.pools),result:212};
  const snapshot={active_scene_seed:seed,state_payload:{decimal_place_value:attempt},active_scene_contract:{scene_version:3}};
  seed.pools.a.ones=0;seed.pools.a.tenths=12;assert.equal(readPlaceValueSnapshot(snapshot),null);
  seed.pools=structuredClone(attempt.pools);seed.result=212;assert.equal(readPlaceValueSnapshot(snapshot),null);
  seed.result=null;seed.last_submission={};assert.equal(readPlaceValueSnapshot(snapshot),null);
});
test('strict reader binds authored identity and rejects catalogue, pool and column corruption',()=>{
  assert.ok(readPlaceValueState(validState()));
  const mutations:((s:any)=>void)[]=[s=>{s.operands[0].value=126;s.operands[0].text='1.26';s.pools.a.hundredths=6;},s=>{s.operands[1].id='a';},s=>{s.places[1]=s.places[0];},s=>{s.pools.extra=zero();},s=>{s.pools.a.ones=true;},s=>{s.pools.a.ones=-1;},s=>{s.pools.a.ones=1.5;},s=>{s.pools.a.hundredths=8;},s=>{s.result=20000;},s=>{s.last_validation={};}];
  for(const mutate of mutations){const s=validState();mutate(s);assert.equal(readPlaceValueState(s),null);}
});
test('equivalent nonnormalized model is readable; submitted feedback stays separate from later edits',()=>{
  const s:any=validState();s.pools={a:zero(),b:zero(),result:{...zero(),ones:1,tenths:10,hundredths:12}};s.result=211;
  s.last_submission={source_ref:s.source_ref,pools:structuredClone(s.pools),result:211};
  s.last_validation={status:'INVALID',feedback_code:'PLACE_VALUE_INVALID',structural_valid:true,model_complete:true,model_correct:true,written_correct:false};
  assert.ok(readPlaceValueState(s));s.result=212;assert.ok(readPlaceValueState(s));
  s.last_validation.written_correct=true;assert.equal(readPlaceValueState(s),null);
});
test('host retains exact historical and new math contract rows',()=>{
  const scene={scene_id:'s',scene_version:1,subject_key:'MATH',subject_profile_version:'subject-profile-v4',activity_key:'decimal_place_value',activity_contract_version:'decimal-place-value-activity-v1',renderer_key:'decimal-place-value',renderer_version:'decimal-place-value-renderer-v1',payload_schema_version:'decimal-place-value-scene-v1',locale:'en',direction:'ltr' as const};
  assert.equal(resolveApprovedStudioRenderer(scene),'MATH_DECIMAL_PLACE_VALUE');
  assert.equal(resolveApprovedStudioRenderer({...scene,subject_profile_version:'subject-profile-v3'}),null);
});
