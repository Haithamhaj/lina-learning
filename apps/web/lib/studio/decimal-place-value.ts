/** Strict projection reader; browser counts never become durable authority. */
export const placeWeights={hundreds:10000,tens:1000,ones:100,tenths:10,hundredths:1} as const;
export type Place=keyof typeof placeWeights;
export type Pool=Record<Place,number>;
export type PlaceValueState={source_ref:string;catalog_version:string;mode:'ADD'|'SUBTRACT';operands:{id:string;value:number;text:string}[];places:{id:Place;weight:number}[];pools:Record<string,Pool>;result:number|null;last_submission?:{source_ref:string;pools:Record<string,Pool>;result:number|null};last_validation?:{status:string;feedback_code:string;structural_valid:boolean;model_complete:boolean;model_correct:boolean;written_correct:boolean|null}};
const record=(x:unknown):x is Record<string,unknown>=>typeof x==='object'&&x!==null&&!Array.isArray(x);
const integer=(x:unknown,max=19998):x is number=>typeof x==='number'&&Number.isInteger(x)&&x>=0&&x<=max;
const keys=(x:Record<string,unknown>,expected:string[])=>Object.keys(x).sort().join('|')===[...expected].sort().join('|');
export function parsePlaceResult(text:string):number|null{
  if(text.length>6)return null;
  const normalized=text.replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-1632)).replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776)).replace(/٫/g,'.');
  if(!/^(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,2})?$/.test(normalized))return null;
  const [whole,fraction='']=normalized.split('.');const value=Number(whole)*100+Number(fraction.padEnd(2,'0'));
  return integer(value)?value:null;
}
export const formatPlaceValue=(n:number)=>`${Math.floor(n/100)}.${String(n%100).padStart(2,'0')}`;
export const poolValue=(p:Pool)=>Object.entries(placeWeights).reduce((sum,[k,w])=>sum+p[k as Place]*w,0);
// Immutable authored operands, not an answer key or browser configuration authority.
const catalog:Record<string,readonly [number,number,string,string]>={
  'add-simple':[123,214,'1.23','2.14'],'add-carry':[127,85,'1.27','0.85'],
  'add-tens':[995,10,'9.95','0.10'],'add-maximum':[9999,9999,'99.99','99.99'],
  'add-zero':[0,120,'0','1.20'],'add-both-zero':[0,0,'0.0','0.00'],
  'subtract-simple':[357,123,'3.57','1.23'],'subtract-zero-chain':[200,75,'2.00','0.75'],
  'subtract-decompose':[230,75,'2.30','0.75'],'subtract-equal':[120,120,'1.2','1.20'],
  'subtract-zero':[9999,0,'99.99','0'],'subtract-both-zero':[0,0,'0','0.00'],
};
export function readPlaceValueState(value:unknown):PlaceValueState|null{
  if(!record(value)||typeof value.source_ref!=='string'||!Object.keys(catalog).some(k=>value.source_ref==='decimal-place:v1:'+k)||value.catalog_version!=='decimal-place-value-catalog-v1'||!['ADD','SUBTRACT'].includes(String(value.mode)))return null;
  if(Object.keys(value).some(k=>!['source_ref','catalog_version','mode','operands','places','pools','result','last_submission','last_validation'].includes(k)))return null;
  if(!value.source_ref.startsWith(value.mode==='ADD'?'decimal-place:v1:add-':'decimal-place:v1:subtract-'))return null;
  if(!Array.isArray(value.operands)||value.operands.length!==2||!Array.isArray(value.places)||value.places.length!==5)return null;
  for(let i=0;i<2;i++){const o=value.operands[i];if(!record(o)||!keys(o,['id','value','text'])||o.id!==['a','b'][i]||!integer(o.value,9999)||typeof o.text!=='string'||parsePlaceResult(o.text)!==o.value)return null;}
  for(let i=0;i<5;i++){const p=value.places[i];const [id,weight]=Object.entries(placeWeights)[i];if(!record(p)||!keys(p,['id','weight'])||p.id!==id||p.weight!==weight)return null;}
  const a=value.operands[0].value as number,b=value.operands[1].value as number;
  const authored=catalog[value.source_ref.slice('decimal-place:v1:'.length)];
  if(a!==authored[0]||b!==authored[1]||value.operands[0].text!==authored[2]||value.operands[1].text!==authored[3])return null;
  const mode=value.mode;
  if(value.mode==='SUBTRACT'&&a<b)return null;
  function poolsValid(pools:unknown):pools is Record<string,Pool>{
    if(!record(pools)||!keys(pools,mode==='ADD'?['a','b','result']:['remaining','removed']))return false;
    let total=0;
    for(const pool of Object.values(pools)){if(!record(pool)||!keys(pool,Object.keys(placeWeights))||!Object.values(pool).every(n=>integer(n)))return false;total+=poolValue(pool as Pool);}
    return total===(mode==='ADD'?a+b:a)&&(mode!=='SUBTRACT'||poolValue(pools.removed as Pool)<=b);
  }
  if(!poolsValid(value.pools)||(value.result!==null&&!integer(value.result)))return null;
  if(value.last_submission!==undefined){const s=value.last_submission;if(!record(s)||!keys(s,['source_ref','pools','result'])||s.source_ref!==value.source_ref||!poolsValid(s.pools)||(s.result!==null&&!integer(s.result)))return null;}
  if(value.last_validation!==undefined){const v=value.last_validation;if(!record(v)||!keys(v,['status','feedback_code','structural_valid','model_complete','model_correct','written_correct'])||!['VALID','INVALID','UNDER_SPECIFIED'].includes(String(v.status))||v.feedback_code!=='PLACE_VALUE_'+v.status||v.structural_valid!==true||typeof v.model_complete!=='boolean'||typeof v.model_correct!=='boolean'||(v.written_correct!==null&&typeof v.written_correct!=='boolean'))return null;}
  if((value.last_submission===undefined)!==(value.last_validation===undefined))return null;
  if(value.last_submission!==undefined){
    const s=value.last_submission as PlaceValueState['last_submission'];
    const v=value.last_validation as PlaceValueState['last_validation'];
    if(!s||!v)return null;
    const complete=mode==='ADD'?poolValue(s.pools.a)===0&&poolValue(s.pools.b)===0:poolValue(s.pools.removed)===b;
    const written=s.result===null?null:s.result===(mode==='ADD'?a+b:a-b);
    const status=!complete||written===null?'UNDER_SPECIFIED':written?'VALID':'INVALID';
    if(v.model_complete!==complete||v.model_correct!==complete||v.written_correct!==written||v.status!==status)return null;
  }
  return value as PlaceValueState;
}

/** Place-value-only projection: never fill holes in a present durable attempt. */
export function readPlaceValueSnapshot(snapshot:{active_scene_seed:unknown;state_payload:Record<string,unknown>;active_scene_contract:{scene_version:number}|null}):PlaceValueState|null{
  const seed=readPlaceValueState(snapshot.active_scene_seed);
  if(!seed||!snapshot.active_scene_contract||!keys(seed,['source_ref','catalog_version','mode','operands','places','pools','result'])||seed.result!==null)return null;
  const initialValues:Record<string,number>=seed.mode==='ADD'?{a:seed.operands[0].value,b:seed.operands[1].value,result:0}:{remaining:seed.operands[0].value,removed:0};
  for(const [pool,value] of Object.entries(initialValues)){
    let rest=value;
    for(const [place,weight] of Object.entries(placeWeights)){
      if(seed.pools[pool][place as Place]!==Math.floor(rest/weight))return null;
      rest%=weight;
    }
  }
  if(!Object.prototype.hasOwnProperty.call(snapshot.state_payload,'decimal_place_value')){
    // Authored activation creates version 1, then activates version 2 before any action.
    return snapshot.active_scene_contract.scene_version===2?seed:null;
  }
  const attempt=snapshot.state_payload.decimal_place_value;
  if(!record(attempt)||!Object.prototype.hasOwnProperty.call(attempt,'pools')||!Object.prototype.hasOwnProperty.call(attempt,'result')||Object.keys(attempt).some(k=>!['pools','result','last_submission','last_validation'].includes(k)))return null;
  return readPlaceValueState({...seed,...attempt});
}
