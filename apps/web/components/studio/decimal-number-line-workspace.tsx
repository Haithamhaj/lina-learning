"use client";

import { useEffect, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import type { StudioOperation } from '@/lib/studio/contracts';
import { DecimalLineState, formatDecimal, parseDecimal, gridValue, majorTicks, unreadableNumberLineCopy } from '@/lib/studio/decimal-number-line';

type Props={sceneId:string;sceneVersion:number;state:DecimalLineState|null;locale:string;onOperation:(operation:StudioOperation)=>Promise<void>;onReload:()=>void};
const button='rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-40';

/** Local state is only a disposable gesture/input draft; Snapshot owns every attempt. */
export function DecimalNumberLineWorkspace({sceneId,sceneVersion,state,locale,onOperation,onReload}:Props){
  const [language,setLanguage]=useState(locale.startsWith('ar')?'ar':'en');
  const [pending,setPending]=useState(false);
  const [error,setError]=useState('');
  const [drafts,setDrafts]=useState<Record<string,string>>({});
  const [preview,setPreview]=useState<{id:string;value:number}|null>(null);
  const axis=useRef<HTMLDivElement>(null);
  const gesture=useRef<{pointer:number;id:string;version:number}|null>(null);
  const busy=useRef(false);
  const ar=language==='ar';
  useEffect(()=>{gesture.current=null;setPreview(null);setDrafts({});},[sceneId,sceneVersion]);
  if(!state){const copy=unreadableNumberLineCopy(locale);return <section dir={locale.startsWith('ar')?'rtl':'ltr'} className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900" role="alert"><p className="font-bold">{copy.title}</p><p className="mt-2">{copy.detail}</p><button type="button" className={`${button} mt-3`} onClick={onReload}>{copy.reload}</button></section>;}
  const s=state;
  async function send(action_key:string,payload:Record<string,unknown>){
    if(busy.current)return;
    busy.current=true;setPending(true);setError('');
    try{await onOperation({scene_id:sceneId,base_scene_version:sceneVersion,action_key,payload,idempotency_key:crypto.randomUUID()});}
    catch{setError(ar?'لم تُحفظ المحاولة. تم طلب حالة الخادم؛ أعد المحاولة بعد التحديث.':'Attempt was not saved. Server state was requested; retry after the update.');}
    finally{busy.current=false;setPending(false);setPreview(null);setDrafts({});}
  }
  const move=(id:string,value:number)=>send('PLACE_POINT',{point_id:id,from_value:s.positions[id],value});
  function pointerValue(event:PointerEvent):number|null{
    const rect=axis.current?.getBoundingClientRect();
    if(!rect||event.clientY<rect.top||event.clientY>rect.bottom)return null;
    return gridValue(event.clientX,rect,s.axis_min,s.axis_max);
  }
  function finish(event:PointerEvent<HTMLButtonElement>){
    const current=gesture.current;
    gesture.current=null;setPreview(null);
    if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId);
    const value=pointerValue(event);
    if(current&&current.pointer===event.pointerId&&current.version===sceneVersion&&value!==null)void move(current.id,value);
  }
  const complete=Object.values(s.positions).every(v=>v!==null)&&s.selection!==null;
  return <section dir={ar?'rtl':'ltr'} className="space-y-4 rounded-2xl bg-slate-50 p-4" aria-label={ar?'خط الأعداد العشرية':'Decimal number line'}>
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-lg font-bold">{ar?'خط الأعداد العشرية':'Decimal number line'}</h3><button type="button" className={button} onClick={()=>setLanguage(ar?'en':'ar')}>{ar?'English':'العربية'}</button></div>
    <p>{s.mode==='COMPARE'?(ar?'ضع النقطتين ثم اختر العلاقة بين أ و ب.':'Place both points, then choose the relation between A and B.'):(ar?`ضع س، ثم قرّب إلى ${s.target_place==='hundredths'?'جزء من مئة':s.target_place==='tenths'?'جزء من عشرة':'الآحاد'}. عند المنتصف قرّب إلى الأعلى.`:`Place X, then round to ${s.target_place}. Midpoints round up.`)}</p>
    <p className="text-sm text-slate-600">{ar?'القيم بوحدات العدد. كل خطوة دقيقة = 0.001. اسحب داخل الخط أو استخدم أدوات الضبط.':'Values are in number units. Fine step = 0.001. Drag within the line or use exact controls.'}</p>
    <div className="px-6" dir="ltr">
      <div ref={axis} className="relative h-40 border-b-2 border-slate-700" data-number-line-axis="true">
        {majorTicks(s.axis_min,s.axis_max).map((value,i)=><div key={i} className="absolute bottom-0 h-3 border-l border-slate-500" style={{left:`${i*20}%`}}><span className="absolute top-4 -translate-x-1/2 text-[10px] tabular-nums">{formatDecimal(value)}</span></div>)}
        {s.points.map((point,index)=>{
          const value=preview?.id===point.id?preview.value:s.positions[point.id];
          const shown=value??s.axis_min;
          return <button key={point.id} type="button" disabled={pending} aria-label={`${point.id.toUpperCase()}: ${point.text}; ${value===null?(ar?'غير موضوعة':'not placed'):formatDecimal(shown)}`}
            className="absolute -translate-x-1/2 touch-none rounded-full border-2 border-blue-700 bg-white px-3 py-2 text-sm font-bold text-blue-900 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:opacity-50"
            style={{left:`${(shown-s.axis_min)/(s.axis_max-s.axis_min)*100}%`,top:index*52+12}}
            onPointerDown={event=>{if(busy.current||!event.isPrimary||event.button!==0)return;gesture.current={pointer:event.pointerId,id:point.id,version:sceneVersion};event.currentTarget.setPointerCapture(event.pointerId);}}
            onPointerMove={event=>{if(gesture.current?.pointer!==event.pointerId)return;const n=pointerValue(event);setPreview(n===null?null:{id:point.id,value:n});}}
            onPointerUp={finish}
            onPointerCancel={()=>{gesture.current=null;setPreview(null);}}
            onLostPointerCapture={()=>{gesture.current=null;setPreview(null);}}
            onKeyDown={event=>{if(event.key==='Escape'){gesture.current=null;setPreview(null);}if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();const next=Math.max(s.axis_min,Math.min(s.axis_max,(value??s.axis_min)+(event.key==='ArrowRight'?1:-1)));void move(point.id,next);}}}
          >{point.id.toUpperCase()} · {point.text}</button>;
        })}
      </div>
    </div>
    <div className="pt-7 space-y-3">
      {s.points.map(point=>{const n=s.positions[point.id];const draft=drafts[point.id]??(n===null?'':formatDecimal(n));const parsed=parseDecimal(draft);return <fieldset key={point.id} disabled={pending} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 p-3">
        <legend className="px-1 text-sm font-bold"><bdi dir="ltr">{point.id.toUpperCase()} = {point.text}</bdi></legend>
        <label className="text-sm">{ar?'الموضع':'Position'} <input aria-label={`${point.id.toUpperCase()} ${ar?'الموضع الدقيق':'exact position'}`} dir="ltr" inputMode="decimal" value={draft} onChange={event=>setDrafts({...drafts,[point.id]:event.target.value})} className="w-24 rounded-lg border border-slate-400 bg-white p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600" maxLength={6}/></label>
        <button type="button" className={button} disabled={parsed===null||parsed<s.axis_min||parsed>s.axis_max} onClick={()=>{if(parsed!==null)void move(point.id,parsed);}}>{ar?'ضع النقطة':'Place point'}</button>
        <button type="button" dir="ltr" className={button} disabled={n===null||n<=s.axis_min} aria-label={`${point.id.toUpperCase()} minus 0.001`} onClick={()=>{if(n!==null)void move(point.id,n-1);}}>−0.001</button>
        <button type="button" dir="ltr" className={button} disabled={n===null||n>=s.axis_max} aria-label={`${point.id.toUpperCase()} plus 0.001`} onClick={()=>{if(n!==null)void move(point.id,n+1);}}>+0.001</button>
        <span className="text-sm" dir="ltr">{n===null?(ar?'غير موضوعة':'Not placed'):formatDecimal(n)}</span>
      </fieldset>;})}
    </div>
    <div className="flex flex-wrap gap-2" role="group" aria-label={ar?'اختر الإجابة':'Choose answer'} dir="ltr">
      {(s.mode==='COMPARE'?['LT','EQ','GT']:s.endpoints).map(choice=><button key={choice} type="button" className={`${button} ${s.selection===choice?'ring-2 ring-blue-600 bg-blue-50':''}`} disabled={pending} aria-pressed={s.selection===choice} onClick={()=>void send('SELECT_ANSWER',{from_selection:s.selection,selection:choice})}>{typeof choice==='number'?formatDecimal(choice):choice==='LT'?'A < B':choice==='EQ'?'A = B':'A > B'}</button>)}
    </div>
    <button type="button" className={button} disabled={pending||!complete} onClick={()=>void send('SUBMIT_CONFIGURATION',{source_ref:s.source_ref,positions:s.positions,selection:s.selection})}>{ar?'أرسل المحاولة إلى المعلّم':'Submit attempt to Tutor'}</button>
    <p role="status" className="text-sm">{pending?(ar?'جارٍ الحفظ…':'Saving…'):s.last_validation?(s.last_validation.status==='VALID'?(ar?'المحاولة المرسلة صحيحة.':'Last submitted attempt is correct.'):(ar?'راجع المحاولة المرسلة، ثم أعد الإرسال.':'Review your submitted attempt, then submit again.')):(ar?'التحريك والاختيار لا يرسلان للمعلّم.':'Moving and choosing do not call the Tutor.')}</p>
    {error?<p role="alert" className="text-sm text-rose-800">{error}</p>:null}
  </section>;
}
