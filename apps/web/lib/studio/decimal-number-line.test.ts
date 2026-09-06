import assert from 'node:assert/strict';
import test from 'node:test';
import { parseDecimal, formatDecimal, gridValue, majorTicks, readDecimalLineState, unreadableNumberLineCopy } from './decimal-number-line';
import { resolveApprovedStudioRenderer } from './renderer-host';

test('exact thousandths parsing and formatting without floating correctness', () => {
  assert.equal(parseDecimal('0.500'), 500);
  assert.equal(parseDecimal('0.5'), 500);
  for (let n=0;n<=10000;n++) assert.equal(parseDecimal(formatDecimal(n)),n);
  for(const text of ['0.0001','-1','1e3','','NaN','10.001']) assert.equal(parseDecimal(text),null);
});
test('geometry maps current rendered bounds to declared grid, outside cancels',()=>{
  assert.equal(gridValue(150,{left:100,width:200},400,500),425);
  assert.equal(gridValue(200,{left:100,width:200},400,500),450);
  assert.equal(gridValue(99,{left:100,width:200},400,500),null);
});
test('a narrow 244px axis uses six separated major labels with exact endpoints',()=>{
  assert.deepEqual(majorTicks(0,1000),[0,200,400,600,800,1000]);
  assert.deepEqual(majorTicks(9000,10000),[9000,9200,9400,9600,9800,10000]);
  assert.ok(244/(majorTicks(0,1000).length-1)>31);
});
test('strict reader preserves coincident point identities and accepts wrong attempts',()=>{
  const seed={source_ref:'decimal-line:v1:compare-equal',catalog_version:'decimal-number-line-catalog-v1',mode:'COMPARE',points:[{id:'a',value:500,text:'0.5'},{id:'b',value:500,text:'0.500'}],axis_min:0,axis_max:1000,grid_step:1,target_place:null,endpoints:[],positions:{a:400,b:500},selection:'GT'};
  assert.ok(readDecimalLineState(seed));
  assert.equal(readDecimalLineState({...seed,positions:{a:0.5,b:500}}),null);
  assert.equal(readDecimalLineState({...seed,points:[seed.points[0],seed.points[0]]}),null);
});
test('host selects exact decimal and explicit v3 Make-Ten, never latest fallback',()=>{
  const scene={scene_id:'s',scene_version:1,subject_key:'MATH',subject_profile_version:'subject-profile-v3',activity_key:'decimal_number_line',activity_contract_version:'decimal-number-line-activity-v1',renderer_key:'decimal-number-line',renderer_version:'decimal-number-line-renderer-v1',payload_schema_version:'decimal-number-line-scene-v1',locale:'en',direction:'auto' as const};
  assert.equal(resolveApprovedStudioRenderer(scene),'MATH_DECIMAL_NUMBER_LINE');
  assert.equal(resolveApprovedStudioRenderer({...scene,subject_profile_version:'subject-profile-v99'}),null);
  assert.equal(resolveApprovedStudioRenderer({...scene,activity_key:'ten_frame_group_transfer',activity_contract_version:'ten-frame-group-transfer-activity-v1',renderer_key:'ten-frame-group-transfer',renderer_version:'ten-frame-group-transfer-renderer-v1',payload_schema_version:'ten-frame-group-transfer-scene-v1'}),'MATH_MAKE_TEN');
});

test('unreadable number-line state has localized recovery copy',()=>{
  assert.deepEqual(unreadableNumberLineCopy('en'),{
    title:'This number line cannot be read safely.',
    detail:'Tutor chat remains available. Reload the Workspace to use the server’s current Studio state.',
    reload:'Reload Workspace',
  });
  assert.deepEqual(unreadableNumberLineCopy('ar-SA'),{
    title:'لا يمكن قراءة خط الأعداد هذا بأمان.',
    detail:'تظل محادثة المعلّم متاحة. أعد تحميل مساحة العمل لاستخدام حالة Studio الحالية من الخادم.',
    reload:'أعد تحميل مساحة العمل',
  });
});
