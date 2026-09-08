"use client";
import React,{useEffect,useId,useRef,useState} from "react";
import {ProcessArt,ProcessScene,ProcessViewAction,ProcessViewState,validateProcess} from "./process-model";

/** Application-owned schematic assets. No runtime SVG strings or model-authored paths. */
function Illustration({kind}:{kind:ProcessArt}) {
 const leaf=<path d="M20 73Q38 28 83 47Q70 91 20 73Z" fill="#b6d6b1" stroke="#577b61" strokeWidth="2"/>;
 return <svg viewBox="0 0 104 100" aria-hidden="true" focusable="false" className="pv-art" x="-60" y="-60" width="120" height="120">
 <circle cx="52" cy="50" r="45" fill="#edf3ee"/>
 {kind==='egg'&&<>{leaf}<ellipse cx="52" cy="51" rx="10" ry="15" fill="#fff5c7" stroke="#8b8151" strokeWidth="2"/><path d="M48 39V63M53 38V64M58 41V61" stroke="#c8b972"/></>}
 {kind==='larva'&&<>{leaf}{[30,40,50,60,70].map((x,i)=><circle key={x} cx={x} cy={58-i*2} r="9" fill={i%2?'#8daa61':'#c4d690'} stroke="#57704b" strokeWidth="2"/>)}<circle cx="73" cy="48" r="2" fill="#263c34"/></>}
 {kind==='pupa'&&<><path d="M20 22L86 29M57 26V37" stroke="#7a6858" strokeWidth="5" strokeLinecap="round"/><path d="M57 36C81 48 67 82 54 82C38 73 39 46 57 36Z" fill="#98bb91" stroke="#476d51" strokeWidth="2"/><path d="M44 52L66 59M45 62L63 70" stroke="#dce8bd" strokeWidth="3"/></>}
 {kind==='butterfly'&&<><path d="M50 49C14 4 5 51 43 60C13 76 34 99 51 66M54 49C90 4 99 51 61 60C91 76 70 99 53 66" fill="#ddb56d" stroke="#56574c" strokeWidth="3"/><path d="M52 42V73M51 44L43 32M54 44L61 32" stroke="#354b43" strokeWidth="4" strokeLinecap="round"/></>}
 {kind==='drop'&&<><path d="M52 19C47 32 29 48 29 62A23 23 0 0 0 75 62C75 47 58 32 52 19Z" fill="#9ac9d6" stroke="#3c7483" strokeWidth="2"/>{[40,53,62].map((x,i)=><circle key={x} cx={x} cy={62+i*4} r="3" fill="#927a59"/>)}</>}
 {kind==='filter'&&<><path d="M20 29H84L57 62V80H47V62Z" fill="#f3e8cd" stroke="#798c87" strokeWidth="3"/><path d="M26 32H78L52 55Z" fill="#d2e3df"/>{[38,48,60,66].map(x=><circle key={x} cx={x} cy="36" r="3" fill="#9a805f"/>)}<path d="M52 84V89" stroke="#549caf" strokeWidth="4"/></>}
 {kind==='vessel'&&<><path d="M30 22V78Q52 91 74 78V22" fill="#e4f0ef" stroke="#6e8c89" strokeWidth="3"/><path d="M33 53Q52 59 71 53V76Q52 86 33 76Z" fill="#91c3d1"/><path d="M29 22H40M64 22H75" stroke="#6e8c89" strokeWidth="3"/></>}
 {kind==='idea'&&<><path d="M41 67C39 56 29 51 30 40C31 13 75 13 75 40C76 52 64 58 63 67Z" fill="#e9d293" stroke="#897747" strokeWidth="2"/><path d="M43 74H61M46 81H58M51 66V45L43 39M52 46L62 38" fill="none" stroke="#897747" strokeWidth="3"/></>}
 {(kind==='draft'||kind==='review')&&<><rect x="27" y="20" width="50" height="64" rx="5" fill="#fffdf5" stroke="#879b91" strokeWidth="2"/>{[34,44,54,64].map(y=><path key={y} d={`M37 ${y}H65`} stroke="#b5c5bb" strokeWidth="3"/>)}{kind==='review'?<path d="M48 67L57 76L79 49" fill="none" stroke="#567d62" strokeWidth="5"/>:<path d="M51 72L77 38L83 43L57 77Z" fill="#d6aa70" stroke="#8e704d" strokeWidth="2"/>}</>}
 </svg>;
}
type Point = {x:number;y:number};
/** Layout depends on topology/count/available space, never a lesson or stage name. */
export function processLayout(scene:ProcessScene,compact:boolean) {
 const n=scene.stages.length;
 const labelRows=Math.max(...scene.stages.map(s=>Math.ceil(s.label.length/18)));
 const topExtra=Math.max(0,labelRows-1)*36, centerY=370+topExtra;
 const step=Math.max(230,175+labelRows*36);
 const height=compact?100+(n-1)*step+130+labelRows*36:760+topExtra*2;
 const positions:Point[]=scene.stages.map((_,i)=>compact?{x:170,y:100+i*step}:scene.topology==='cycle'?{x:500+290*Math.cos(-Math.PI/2+i*2*Math.PI/n),y:centerY+230*Math.sin(-Math.PI/2+i*2*Math.PI/n)}:{x:120+i*760/(n-1),y:320});
 const paths=scene.relations.map((r,i)=>{
  if(compact){const a=positions[i],b=positions[(i+1)%n];return i===n-1?`M 104 ${a.y} H 28 V ${b.y} H 104`:`M 236 ${a.y} C 310 ${a.y},310 ${b.y},236 ${b.y}`;}
  if(scene.topology==='sequence'){const a=positions[i],b=positions[i+1];return `M ${a.x+67} ${a.y} L ${b.x-70} ${b.y}`;}
  const angle=-Math.PI/2+i*2*Math.PI/n,gap=Math.min(.22,Math.PI/n/3),end=angle+2*Math.PI/n-gap;
  const point=(t:number)=>({x:500+210*Math.cos(t),y:centerY+160*Math.sin(t)});
  const a=point(angle+gap),b=point(end);
  return `M ${a.x} ${a.y} A 210 160 0 ${2*Math.PI/n-2*gap>Math.PI?1:0} 1 ${b.x} ${b.y}`;
 });
 return {positions,paths,width:compact?340:1000,height,centerY,topExtra,labelRows};
}

export function ProcessView({scene,state,onAction,onExplain,reducedMotion=false}:{scene:ProcessScene;state:ProcessViewState;onAction:(action:ProcessViewAction)=>void;onExplain:(id:string)=>void;reducedMotion?:boolean}) {
 const container=useRef<HTMLDivElement>(null);
 const [compact,setCompact]=useState(false);
 const marker=useId().replace(/:/g,'');
 useEffect(()=>{const el=container.current;if(!el)return;const observer=new ResizeObserver(entries=>setCompact(entries[0].contentRect.width<620));observer.observe(el);return()=>observer.disconnect();},[]);
 const ar=scene.locale==='ar';
 if(!validateProcess(scene))return <section role="status">{ar?'هذا العرض غير متاح. يمكنك متابعة الشرح النصّي.':'This visual is unavailable. Continue with a text explanation.'}</section>;
 const {positions,paths,width,height,centerY,topExtra,labelRows}=processLayout(scene,compact);
 const selected=scene.stages.find(s=>s.id===state.selectedId);
 const active=scene.stages.find(s=>s.id===state.activeExplanationStageId);
 const shown=active&&state.revealedIds.includes(active.id);
 const returnRelation=scene.topology==='cycle'?scene.relations[scene.relations.length-1]:null;
 const highlighted=scene.relations.find(r=>state.highlightedRelationIds?.includes(r.id));
 const focus=state.focusedStageId??state.selectedId;
 function moveFocus(event:React.KeyboardEvent<SVGGElement>,i:number) {
  if(event.key==='Enter'||event.key===' '){event.preventDefault();onAction({type:'focus',id:scene.stages[i].id});return;}
  if(!['ArrowDown','ArrowUp','ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
  event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?scene.stages.length-1:(i+(['ArrowDown','ArrowRight'].includes(event.key)?1:-1)+scene.stages.length)%scene.stages.length;
  container.current?.querySelectorAll<SVGGElement>('[data-stage]')[next]?.focus();
 }
 const motion=new Set(scene.motion_intents??[]);
 return <section className={`pv ${Array.from(motion).map(value=>`pv-motion-${value.toLowerCase()}`).join(' ')}`} data-reduced={reducedMotion} dir={ar?'rtl':'ltr'} lang={scene.locale} aria-label={scene.title}>
 <style>{styles}</style>
 <header className="pv-header"><span className="pv-kicker">{ar?'اكتشف الروابط':'Explore the connections'}</span><h1>{scene.title}</h1><p>{scene.subtitle}</p></header>
 <div ref={container} className="pv-diagram" data-layout={compact?'vertical-spatial':scene.topology==='cycle'?'radial':'sequence'}>
 <svg className="pv-scene" viewBox={`0 0 ${width} ${height}`} aria-label={ar?'مراحل وروابط موجّهة؛ اختر مرحلة لاستكشافها':'Stages and directed relations; select a stage to explore'}>
 <defs><marker id={`${marker}-arrow`} viewBox="0 0 12 12" refX="10" refY="6" markerWidth="18" markerHeight="18" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M 1 1 L 10 6 L 1 11 Z" fill="#52715d" stroke="#52715d" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/></marker><marker id={`${marker}-return`} viewBox="0 0 12 12" refX="10" refY="6" markerWidth="18" markerHeight="18" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M 1 1 L 10 6 L 1 11 Z" fill="#95651e" stroke="#95651e" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/></marker></defs>
 {!compact&&scene.topology==='cycle'&&<ellipse cx="500" cy={centerY} rx="210" ry="160" fill="#f0f4eb" stroke="#e1e9dc" strokeWidth="1"/>}
 <g aria-hidden="true">{scene.relations.map((r,i)=>{
 const returning=returnRelation?.id===r.id,emphasized=state.highlightedRelationIds?.includes(r.id)||motion.has('EMPHASIZE_RELATION'),traced=state.tracingRelationId===r.id||motion.has('TRACE_SEQUENCE')||motion.has('TRACE_CYCLE');
 return <g key={r.id} data-relation={r.id} className={`pv-relation ${returning?'pv-return':''} ${emphasized?'pv-relation-active':''}`}>
 <path className="pv-relation-path" d={paths[i]} fill="none" markerEnd={`url(#${marker}-${returning?'return':'arrow'})`}/>
 {traced&&<path className="pv-trace" d={paths[i]} fill="none" pathLength="1" markerEnd={`url(#${marker}-${returning?'return':'arrow'})`}/>}</g>;
 })}</g>
 {!compact&&scene.topology==='cycle'&&<g className="pv-center" aria-hidden="true"><text x="500" y={centerY-20} textAnchor="middle">{focus?(ar?`المرحلة ${scene.stages.findIndex(s=>s.id===focus)+1} من ${scene.stages.length}`:`Stage ${scene.stages.findIndex(s=>s.id===focus)+1} of ${scene.stages.length}`):ar?`${scene.stages.length} مراحل`:`${scene.stages.length} stages`}</text><text x="500" y={centerY+19} textAnchor="middle" className="pv-center-sub">{ar?'تتبّع اتجاه الأسهم':'Follow the arrows'}</text></g>}
 {scene.stages.map((stage,i)=>{
 const p=positions[i],emphasized=state.highlightedStageIds?.includes(stage.id)||focus===stage.id||motion.has('TRANSITION_FOCUS');
 const labelTop=compact?p.y+72:scene.topology==='cycle'&&i===0?p.y-110-topExtra:p.y+78;
 return <g key={stage.id} data-stage={stage.id} role="button" tabIndex={0} aria-pressed={state.selectedId===stage.id} aria-label={`${i+1}. ${stage.label}`} className={`pv-stage ${emphasized?'pv-stage-active':''} ${focus&&!emphasized?'pv-stage-muted':''}`} onClick={()=>onAction({type:'focus',id:stage.id})} onFocus={()=>{if(focus!==stage.id)onAction({type:'focus',id:stage.id});}} onKeyDown={e=>moveFocus(e,i)}>
 <g transform={`translate(${p.x} ${p.y})`}><circle className="pv-focus-ring" r="70"/><g className="pv-symbol"><Illustration kind={stage.art}/></g><circle className="pv-index-disc" cx="-49" cy="-49" r="15"/><text className="pv-index" x="-49" y="-44" textAnchor="middle">{i+1}</text>{state.revealedIds.includes(stage.id)&&<path className="pv-detail-mark" d="M 44 41 H 58 M 44 47 H 58 M 44 53 H 54"/>}</g>
 <foreignObject x={p.x-(compact?100:110)} y={labelTop} width={compact?200:220} height={labelRows*36+40} overflow="visible"><div className="pv-stage-label" dir={ar?'rtl':'ltr'}><bdi>{stage.label}</bdi>{emphasized&&<small>{ar?'موضع التركيز':'In focus'}</small>}</div></foreignObject>
 </g>;
 })}
 </svg>
 </div>
 {returnRelation&&<p className="pv-return-caption"><span aria-hidden="true">↶</span><span>{returnRelation.label} · <bdi>{scene.stages[0].label}</bdi></span></p>}
 <aside className="pv-observation" aria-live="polite"><span className="pv-kicker">{ar?'نستكشف مرحلة':'A closer look'}</span>
 <h2>{active?active.label:ar?'اختر مرحلة في الرسم':'Choose a stage in the scene'}</h2>
 {shown?<p className="pv-detail" key={active.id}>{active.detail}</p>:<p>{ar?'تبقى الدورة كاملة ظاهرة أثناء استكشاف التفاصيل.':'The whole process stays visible while you explore a detail.'}</p>}
 {highlighted&&<p className="pv-relation-summary"><bdi>{scene.stages.find(s=>s.id===highlighted.from)?.label}</bdi><span aria-hidden="true"> → </span><bdi>{scene.stages.find(s=>s.id===highlighted.to)?.label}</bdi> · {highlighted.label}</p>}
 {active&&<button className="pv-explain" onClick={()=>onAction({type:'reveal',id:active.id})}>{ar?'أظهر التفاصيل':'Reveal details'}</button>}
 {highlighted&&<button className="pv-explain" onClick={()=>onAction({type:'trace',id:highlighted.id})}>{ar?'تتبّع هذه العلاقة':'Trace this relationship'}</button>}
 <button className="pv-explain" disabled={!selected} onClick={()=>selected&&onExplain(selected.id)}>{ar?'اشرح هذه المرحلة':'Explain this stage'}</button>
 {highlighted&&<button className="pv-explain" onClick={()=>onExplain(highlighted.id)}>{ar?'اشرح هذه العلاقة':'Explain this relationship'}</button>}</aside>
 <details className="pv-text-equivalent"><summary>{ar?'الوصف النصّي لجميع المراحل والروابط':'Text equivalent: all stages and relationships'}</summary><ol>{scene.stages.map(s=><li key={s.id}><strong>{s.label}:</strong> {s.detail}</li>)}</ol><ul>{scene.relations.map(r=><li key={r.id}>{scene.stages.find(s=>s.id===r.from)?.label} → {scene.stages.find(s=>s.id===r.to)?.label}: {r.label}</li>)}</ul></details>
 <footer className="pv-source">{ar?'مرجع الشرح: ':'Instructional reference: '}<bdi>{scene.sourceLabel}</bdi></footer>
 </section>;
}
const styles=`
.pv{--ink:#263e36;--green:#456b58;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,sans-serif;background:#fffefa;border:1px solid #dfe5d9;border-radius:28px;padding:30px;max-width:1100px;margin:auto;box-sizing:border-box}.pv *{box-sizing:border-box}.pv-header{max-width:850px}.pv-kicker{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:#587361;font-weight:700}.pv h1{font-size:2rem;line-height:1.3;margin:10px 0}.pv-header p{font-size:1.05rem;line-height:1.65;color:#53625b;margin:0}.pv-diagram{direction:ltr;width:100%;margin:4px auto 0}.pv-scene{display:block;width:100%;height:auto;overflow:visible}.pv-stage{cursor:pointer;outline:none}.pv-symbol{opacity:1;transition:opacity 220ms ease-out}.pv-stage-muted .pv-symbol{opacity:.55}.pv-focus-ring{fill:transparent;stroke:transparent;stroke-width:3;transition:fill 220ms,stroke 220ms}.pv-stage-active .pv-focus-ring,.pv-motion-transition_focus .pv-focus-ring{fill:#e5efdc;stroke:#436c53;stroke-width:3}.pv-stage:focus-visible .pv-focus-ring{stroke:#966421;stroke-width:4;stroke-dasharray:5 4}.pv-index-disc{fill:#fffefa;stroke:#bacab8;stroke-width:1}.pv-index{font-size:14px;fill:#365442}.pv-detail-mark{fill:none;stroke:#456b58;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.pv-stage-label{text-align:center;font-size:20px;font-weight:650;line-height:1.45;overflow-wrap:anywhere;color:#263e36}.pv-stage-label small{display:block;font-size:13px;font-weight:500;color:#456b58;margin-top:3px}.pv-stage-label bdi{unicode-bidi:plaintext}.pv-relation-path{stroke:#8ba38a;stroke-width:2.5;transition:stroke-width 220ms,stroke 220ms}.pv-return .pv-relation-path{stroke:#a77d38;stroke-dasharray:7 6;stroke-width:3}.pv-relation-active .pv-relation-path,.pv-motion-emphasize_relation .pv-relation-path{stroke:#436c53;stroke-width:6}.pv-return.pv-relation-active .pv-relation-path{stroke:#95651e;stroke-width:6}.pv-trace{stroke:#446c50;stroke-width:7;stroke-dasharray:1;stroke-dashoffset:0;animation:pv-draw 900ms linear both;pointer-events:none}.pv-return .pv-trace{stroke:#95651e}@keyframes pv-draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}.pv-motion-reveal_in_order .pv-stage{animation:pv-reveal 300ms ease-out both}.pv-motion-reveal_in_order .pv-stage:nth-of-type(2){animation-delay:90ms}@keyframes pv-reveal{from{opacity:.7}to{opacity:1}}.pv-center text{font-size:22px;fill:#45604e;font-weight:600}.pv-center .pv-center-sub{font-size:18px;fill:#627660;font-weight:400}.pv-return-caption{display:flex;gap:12px;align-items:center;font-size:.9rem;line-height:1.65;background:#f6f0e0;color:#74531f;padding:12px 16px;border-radius:12px;margin:0 0 18px}.pv-return-caption>span:first-child{font-size:24px}.pv-observation{border-inline-start:3px solid #88a582;background:#f0f4ec;padding:18px 22px;border-radius:0 14px 14px 0}.pv-observation h2{font-size:1.3rem;margin:7px 0}.pv-observation p{font-size:1.05rem;line-height:1.7;margin:6px 0 12px}.pv-detail{animation:pv-detail-in 200ms ease-out}@keyframes pv-detail-in{from{opacity:.85}to{opacity:1}}.pv-observation .pv-relation-summary{font-size:.85rem;color:#52694f}.pv-explain{font:inherit;background:#fffefa;border:1px solid #91a68f;border-radius:9px;color:#456b58;padding:11px 16px;min-height:44px;cursor:pointer}.pv-explain:disabled{opacity:.6;cursor:default}.pv button:focus-visible,.pv summary:focus-visible{outline:3px solid #966421;outline-offset:3px}.pv-text-equivalent{margin-top:20px;font-size:.9rem;line-height:1.8}.pv-text-equivalent summary{cursor:pointer}.pv-source{font-size:.76rem;line-height:1.7;color:#687769;margin-top:18px}.pv[dir=rtl] .pv-kicker{letter-spacing:0}.pv[dir=rtl] .pv-stage-label{line-height:1.8}.pv[data-reduced=true] *{animation:none!important;transition:none!important}.pv[data-reduced=true] .pv-trace{stroke-dashoffset:0}@media(max-width:600px){.pv{padding:20px 12px;border-radius:20px}.pv h1{font-size:1.65rem}.pv-observation{padding:16px}.pv-header p{font-size:1rem}.pv-stage-label{font-size:20px}}@media(prefers-reduced-motion:reduce){.pv *{animation:none!important;transition:none!important}.pv-trace{stroke-dashoffset:0}}
`;
