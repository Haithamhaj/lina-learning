/** Integer thousandths only. Pixel snapping selects an attempt, never correctness. */
export type DecimalLineState = {
  source_ref: string; catalog_version: string; mode: 'COMPARE'|'ROUND';
  points: {id:string;value:number;text:string}[];
  axis_min:number;axis_max:number;grid_step:1;target_place:null|'ones'|'tenths'|'hundredths';
  endpoints:number[];positions:Record<string,number|null>;selection:string|number|null;
  last_validation?:{status:string;feedback_code:string};
};
const record=(x:unknown):x is Record<string,unknown>=>typeof x==='object'&&x!==null&&!Array.isArray(x);
const exact=(x:unknown):x is number=>typeof x==='number'&&Number.isInteger(x)&&x>=0&&x<=10000;
export function parseDecimal(text:string):number|null {
  if(!/^(?:0|[1-9][0-9]?)(?:\.[0-9]{1,3})?$/.test(text))return null;
  const [whole,fraction='']=text.split('.');
  const value=Number(whole)*1000+Number(fraction.padEnd(3,'0'));
  return exact(value)?value:null;
}
export function formatDecimal(n:number):string {
  return `${Math.floor(n/1000)}.${String(n%1000).padStart(3,'0')}`;
}
export function unreadableNumberLineCopy(locale:string):{title:string;detail:string;reload:string}{
  return locale.startsWith('ar')?{
    title:'لا يمكن قراءة خط الأعداد هذا بأمان.',
    detail:'تظل محادثة المعلّم متاحة. أعد تحميل مساحة العمل لاستخدام حالة Studio الحالية من الخادم.',
    reload:'أعد تحميل مساحة العمل',
  }:{
    title:'This number line cannot be read safely.',
    detail:'Tutor chat remains available. Reload the Workspace to use the server’s current Studio state.',
    reload:'Reload Workspace',
  };
}
export function majorTicks(min:number,max:number):number[]{
  return Array.from({length:6},(_,i)=>min+(max-min)*i/5);
}
export function gridValue(x:number,rect:{left:number;width:number},min:number,max:number):number|null {
  if(!Number.isFinite(x)||!Number.isFinite(rect.width)||rect.width<=0||x<rect.left||x>rect.left+rect.width)return null;
  return min+Math.round((x-rect.left)/rect.width*(max-min));
}
export function readDecimalLineState(value:unknown):DecimalLineState|null {
  if(!record(value)||typeof value.source_ref!=='string'||!value.source_ref.startsWith('decimal-line:v1:')||value.catalog_version!=='decimal-number-line-catalog-v1'||!['COMPARE','ROUND'].includes(String(value.mode)))return null;
  if(!exact(value.axis_min)||!exact(value.axis_max)||value.axis_min>=value.axis_max||value.grid_step!==1||!Array.isArray(value.points)||!record(value.positions)||!Array.isArray(value.endpoints))return null;
  const ids=value.mode==='COMPARE'?['a','b']:['x'];
  if(value.points.length!==ids.length||Object.keys(value.positions).sort().join()!==ids.join())return null;
  const min=value.axis_min,max=value.axis_max;
  for(let i=0;i<ids.length;i++){
    const point=value.points[i],position=value.positions[ids[i]];
    if(!record(point)||point.id!==ids[i]||!exact(point.value)||point.value<min||point.value>max||typeof point.text!=='string'||parseDecimal(point.text)!==point.value)return null;
    if(position!==null&&(!exact(position)||position<min||position>max))return null;
  }
  if(!value.endpoints.every(n=>exact(n)&&n>=min&&n<=max)||new Set(value.endpoints).size!==value.endpoints.length)return null;
  if(value.mode==='COMPARE'){
    if(value.target_place!==null||value.endpoints.length!==0||!(value.selection===null||['LT','EQ','GT'].includes(String(value.selection))))return null;
  }else{
    if(!['ones','tenths','hundredths'].includes(String(value.target_place))||value.endpoints.length<1||value.endpoints.length>2||!(value.selection===null||(exact(value.selection)&&value.endpoints.includes(value.selection))))return null;
  }
  if(value.last_validation!==undefined&&(!record(value.last_validation)||!['VALID','INVALID'].includes(String(value.last_validation.status))||!['DECIMAL_LINE_CORRECT','DECIMAL_LINE_TRY_AGAIN'].includes(String(value.last_validation.feedback_code))))return null;
  return value as DecimalLineState;
}
