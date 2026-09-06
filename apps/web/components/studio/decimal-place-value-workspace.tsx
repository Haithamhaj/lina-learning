"use client";
import {useEffect,useRef,useState} from 'react';
import type {PointerEvent} from 'react';
import type {StudioOperation} from '../../lib/studio/contracts';
import {Place,PlaceValueState,formatPlaceValue,parsePlaceResult,placeWeights,poolValue} from '../../lib/studio/decimal-place-value';

type Props={sceneId:string;sceneVersion:number;state:PlaceValueState|null;locale:string;onOperation:(operation:StudioOperation)=>Promise<void>;onReload:()=>void};
const button='rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:opacity-40';
const placeAr={hundreds:'مئات',tens:'عشرات',ones:'آحاد',tenths:'أعشار',hundredths:'أجزاء من مئة'};

export function DecimalPlaceValueWorkspace({sceneId,sceneVersion,state,locale,onOperation,onReload}:Props){
  const [ar,setAr]=useState(locale.startsWith('ar'));
  const [selected,setSelected]=useState<{pool:string;place:Place}|null>(null);
  const [draft,setDraft]=useState<string|null>(null);
  const [pending,setPending]=useState(false);const [error,setError]=useState('');
  const busy=useRef(false);
  const gesture=useRef<{id:number;pool:string;place:Place;version:number}|null>(null);
  useEffect(()=>{gesture.current=null;setSelected(null);setDraft(null);setError('');},[sceneId]);
  useEffect(()=>{gesture.current=null;},[sceneVersion]);
  if(!state)return <section role="alert" className="rounded-xl bg-rose-50 p-4"><p>{ar?'تعذّر فتح مساحة العمل. المحادثة متاحة.':'This workspace could not be opened. Tutor chat remains available.'}</p><button className={button} onClick={onReload}>{ar?'أعد تحميل مساحة العمل':'Reload Workspace'}</button></section>;
  const s=state;const places=Object.keys(placeWeights) as Place[];
  const poolLabel=(pool:string)=>ar?({a:'العدد الأول',b:'العدد الثاني',result:'المجموع',remaining:'المتبقي',removed:'المطروح'}[pool]??pool):({a:'First operand',b:'Second operand',result:'Combined result',remaining:'Remaining',removed:'Removed'}[pool]??pool);
  async function send(action_key:string,payload:Record<string,unknown>){
    if(busy.current)return false;busy.current=true;setPending(true);setError('');
    try{await onOperation({scene_id:sceneId,base_scene_version:sceneVersion,action_key,payload,idempotency_key:crypto.randomUUID()});return true;}
    catch{setError(ar?'لم تُحفظ العملية. أُعيد طلب حالة الخادم؛ راجعها ثم حاول مجددًا.':'Operation was not saved. Server state was requested; review it and retry.');return false;}
    finally{busy.current=false;setPending(false);}
  }
  function exchange(pool:string,place:Place,direction:'UP'|'DOWN'){return send('EXCHANGE',{from_pools:s.pools,pool,place,direction});}
  function transfer(source:string,target:string,place:Place,count:number){return send('TRANSFER',{from_pools:s.pools,source,target,place,count});}
  function finish(event:PointerEvent<HTMLButtonElement>){
    const g=gesture.current;gesture.current=null;
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId);
    if(!g||g.id!==event.pointerId||g.version!==sceneVersion||busy.current)return;
    const target=document.elementFromPoint(event.clientX,event.clientY)?.closest<HTMLElement>('[data-place-cell]');
    if(!target)return;
    const pool=target.dataset.pool,place=target.dataset.place as Place;
    if(!pool||!place)return;
    if(pool===g.pool){const delta=places.indexOf(place)-places.indexOf(g.place);if(Math.abs(delta)===1)void exchange(pool,g.place,delta===1?'DOWN':'UP');}
    else if(place===g.place&&((s.mode==='ADD'&&['a','b'].includes(g.pool)&&pool==='result')||(s.mode==='SUBTRACT'&&['remaining','removed'].includes(pool))))void transfer(g.pool,pool,place,1);
  }
  const selection=selected&&s.pools[selected.pool]?selected:null;
  const count=selection?s.pools[selection.pool][selection.place]:0;
  const index=selection?places.indexOf(selection.place):-1;
  const target=selection?(s.mode==='ADD'?(['a','b'].includes(selection.pool)?'result':null):(selection.pool==='remaining'?'removed':'remaining')):null;
  const resultText=draft??(s.result===null?'':formatPlaceValue(s.result));const parsed=parsePlaceResult(resultText);
  const unsaved=draft!==null&&(parsed===null||parsed!==s.result);
  const validation=s.last_validation;
  return <section aria-label={ar?'القيمة المكانية العشرية':'Decimal place value'} dir={ar?'rtl':'ltr'} className="space-y-4 rounded-2xl bg-slate-50 p-3 sm:p-4">
    <header className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-bold">{ar?'نبني العدد ونعيد التجميع':'Build and regroup'}</h3><button className={button} onClick={()=>setAr(!ar)}>{ar?'English':'العربية'}</button></header>
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-3"><p className="text-sm">{ar?'المسألة الأصلية':'Original problem'}</p><p dir="ltr" className="text-center text-2xl font-bold tabular-nums">{s.operands[0].text} {s.mode==='ADD'?'+':'−'} {s.operands[1].text}</p></div>
    <p className="text-sm leading-6">{s.mode==='ADD'?(ar?'انقل الكميات إلى المجموع. يمكنك تجميع عشرة في وحدة أكبر أو تفكيك وحدة إلى عشرة.':'Move quantities into the combined result. Group ten units into one larger unit, or split one into ten.'):(ar?'فكّك الوحدات عند الحاجة، ثم انقل مقدار العدد الثاني إلى المطروح.':'Split units when needed, then move the second operand’s quantity into Removed.')}</p>
    <p className="text-xs text-slate-600">{ar?'اختر خلية واستخدم الأزرار، أو اسحب وحدة إلى خلية مجاورة في الصف للتبادل أو إلى صف الهدف في العمود نفسه للنقل. لا يلزم تطبيع النتيجة.':'Choose a cell and use the buttons, or drag to an adjacent column in the same row to exchange, or the target row in the same column to move one unit. A normalized result is optional.'}</p>
    <div dir="ltr" role="table" aria-label={ar?'جدول القيم المكانية':'Place-value table'} className="space-y-3">
      <div role="row" className="grid grid-cols-5 gap-1">{places.map(place=><div role="columnheader" key={place} className="text-center text-[10px] sm:text-xs font-semibold">{ar?placeAr[place]:place}<div dir="ltr">{formatPlaceValue(placeWeights[place])}</div></div>)}</div>
      {Object.entries(s.pools).map(([pool,counts])=><div key={pool} role="rowgroup" className="rounded-xl border border-slate-200 bg-white p-2"><p className="mb-2 flex justify-between text-xs font-semibold"><span>{poolLabel(pool)}</span><span>{formatPlaceValue(poolValue(counts))}</span></p><div role="row" className="grid grid-cols-5 gap-1">{places.map(place=><div role="cell" key={place}><button type="button" data-place-cell="true" data-pool={pool} data-place={place} aria-label={`${poolLabel(pool)} ${ar?placeAr[place]:place}: ${counts[place]}`} aria-pressed={selection?.pool===pool&&selection.place===place} disabled={pending}
        className={`min-h-12 w-full touch-none rounded-lg border p-1 text-base font-bold tabular-nums focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700 ${selection?.pool===pool&&selection.place===place?'border-blue-600 bg-blue-100':'border-slate-300 bg-slate-50'}`}
        onClick={()=>setSelected({pool,place})}
        onPointerDown={e=>{if(busy.current||!e.isPrimary||e.button!==0)return;setSelected({pool,place});gesture.current={id:e.pointerId,pool,place,version:sceneVersion};e.currentTarget.setPointerCapture(e.pointerId);}}
        onPointerUp={finish} onPointerCancel={()=>{gesture.current=null;}} onLostPointerCapture={()=>{gesture.current=null;}}
        onKeyDown={e=>{if(e.key==='Escape')gesture.current=null;}}>{counts[place]}<span className="block text-[9px] font-normal">× {formatPlaceValue(placeWeights[place])}</span></button></div>)}</div></div>)}
    </div>
    <fieldset disabled={pending||!selection} className="space-y-2 rounded-xl border border-slate-200 p-3"><legend className="text-sm font-semibold">{selection?`${poolLabel(selection.pool)} · ${ar?placeAr[selection.place]:selection.place}`:(ar?'اختر خلية':'Choose a cell')}</legend>
      <div className="flex flex-wrap gap-2"><button className={button} disabled={!selection||index>=4||count<1} onClick={()=>{if(selection)void exchange(selection.pool,selection.place,'DOWN');}}>{ar?'فكّك ١ إلى ١٠':'Split 1 into 10'}</button>
      <button className={button} disabled={!selection||index<=0||count<10} onClick={()=>{if(selection)void exchange(selection.pool,selection.place,'UP');}}>{ar?'جمّع ١٠ في ١':'Group 10 into 1'}</button>
      <button className={button} disabled={!target||count<1} onClick={()=>{if(selection&&target)void transfer(selection.pool,target,selection.place,1);}}>{ar?'انقل وحدة':'Move 1 unit'}</button>
      <button className={button} disabled={!target||count<1} onClick={()=>{if(selection&&target)void transfer(selection.pool,target,selection.place,count);}}>{ar?'انقل كل وحدات الخلية':'Move all in cell'}</button></div>
    </fieldset>
    <div className="flex flex-wrap items-end gap-2"><label className="text-sm font-semibold">{ar?'نتيجتي المكتوبة':'My written result'}<input dir="ltr" inputMode="decimal" maxLength={6} value={resultText} onChange={e=>setDraft(e.target.value)} disabled={pending} className="mt-1 block w-32 rounded-lg border border-slate-400 p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"/></label><button className={button} disabled={pending||parsed===null} onClick={()=>{if(parsed!==null)void send('SET_RESULT',{from_result:s.result,result:parsed}).then(saved=>{if(saved)setDraft(null);});}}>{ar?'احفظ النتيجة':'Save result'}</button><button className={button} disabled={pending||s.result===null} onClick={()=>void send('SET_RESULT',{from_result:s.result,result:null}).then(saved=>{if(saved)setDraft(null);})}>{ar?'امسح النتيجة':'Clear result'}</button></div>
    {unsaved?<p className="text-xs">{ar?'احفظ عددًا صالحًا حتى منزلتين عشريتين قبل الإرسال.':'Save a valid number with at most two decimal places before submitting.'}</p>:null}
    <button className={`${button} border-blue-700 text-blue-900`} disabled={pending||unsaved} onClick={()=>void send('SUBMIT_CONFIGURATION',{source_ref:s.source_ref,pools:s.pools,result:s.result})}>{ar?'أرسل المحاولة إلى المعلّم':'Submit attempt to Tutor'}</button>
    <p role="status" className="text-sm">{pending?(ar?'جارٍ الحفظ…':'Saving…'):validation?(validation.status==='VALID'?(ar?'النموذج والنتيجة صحيحان.':'The submitted model and result are correct.'):validation.status==='UNDER_SPECIFIED'?(ar?'المحاولة محفوظة؛ أكمل النقل والنتيجة.':'Attempt saved; finish the model and written result.'):(ar?'النموذج مكتمل؛ راجع النتيجة المكتوبة.':'Model complete; check the written result.')):(ar?'التبادل والنقل وحفظ النتيجة لا يستدعي المعلّم.':'Exchanges, transfers and saved results do not call the Tutor.')}</p>
    {error?<p role="alert" className="text-sm text-rose-800">{error}</p>:null}
  </section>;
}
