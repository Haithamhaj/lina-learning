export type ProcessArt = 'drop' | 'filter' | 'vessel' | 'egg' | 'larva' | 'pupa' | 'butterfly' | 'idea' | 'draft' | 'review';
export type ProcessStage = {id:string; label:string; detail:string; art:ProcessArt};
export type ProcessMotionIntent='REVEAL_IN_ORDER'|'TRACE_SEQUENCE'|'TRACE_CYCLE'|'TRANSITION_FOCUS'|'EMPHASIZE_RELATION';
export type ProcessScene = {title:string; subtitle:string; locale:'en'|'ar'; topology:'sequence'|'cycle'; stages:ProcessStage[]; relations:{id:string;from:string;to:string;label:string}[]; sourceLabel:string; sourceUrl?:string;motion_intents?:ProcessMotionIntent[]};
export type ProcessViewState = {
 selectedId:string|null; revealedIds:string[]; focusedStageId:string|null;
 highlightedStageIds:string[]; highlightedRelationIds:string[];
 activeExplanationStageId:string|null; tracingRelationId:string|null;
};
export type ProcessViewAction = {type:'select'|'focus'|'reveal'|'trace';id:string}|{type:'clear'};
export function initialProcessState():ProcessViewState {
 return {selectedId:null,revealedIds:[],focusedStageId:null,highlightedStageIds:[],highlightedRelationIds:[],activeExplanationStageId:null,tracingRelationId:null};
}
/** Presentation validation only; source entailment and Studio admission remain outside this view. */
export function validateProcess(scene: Pick<ProcessScene,'topology'|'stages'|'relations'>):boolean {
 if(!['sequence','cycle'].includes(scene.topology)||scene.stages.length<2||scene.stages.length>8)return false;
 const ids=scene.stages.map(s=>s.id);
 if(new Set(ids).size!==ids.length||scene.stages.some(s=>!s.id||!s.label||s.label.length>80||s.detail.length>300))return false;
 const expected=scene.stages.length-(scene.topology==='sequence'?1:0);
 return new Set(scene.relations.map(r=>r.id)).size===scene.relations.length&&scene.relations.every(r=>typeof r.id==='string'&&r.id.length>0&&r.id.length<=64)&&scene.relations.length===expected&&scene.relations.every((r,i)=>r.from===ids[i]&&r.to===ids[(i+1)%ids.length]&&!!r.label&&r.label.length<=120);
}
/** Shared semantic control path for pointer, keyboard and preview commands. No timing or persistence. */
export function nextViewState(scene:Pick<ProcessScene,'stages'|'relations'>,state:ProcessViewState,action:ProcessViewAction):ProcessViewState {
 if(action.type==='clear')return initialProcessState();
 if(action.type==='trace') {
  if(!scene.relations.some(r=>r.id===action.id))return state;
  return {...state,highlightedRelationIds:[action.id],tracingRelationId:action.id};
 }
 if(!scene.stages.some(s=>s.id===action.id))return state;
 const revealedIds=Array.from(new Set([...state.revealedIds,action.id]));
 if(action.type==='reveal')return {...state,revealedIds,activeExplanationStageId:action.id};
 const outgoing=scene.relations.find(r=>r.from===action.id);
 return {...state,selectedId:action.id,focusedStageId:action.id,revealedIds,
 highlightedStageIds:[action.id],highlightedRelationIds:outgoing?[outgoing.id]:[],
 activeExplanationStageId:action.id,tracingRelationId:null};
}

/** Strict authored-review input reader, not a production Tutor/Studio contract. */
export function readProcessScene(value:unknown):ProcessScene|null {
 if(!value||typeof value!=='object'||Array.isArray(value))return null;
 const o=value as Record<string,unknown>;
 const keys=['title','subtitle','locale','topology','stages','relations','sourceLabel','sourceUrl','motion_intents'];
 if(Object.keys(o).some(k=>!keys.includes(k))||!['en','ar'].includes(String(o.locale)))return null;
 if(['title','subtitle','sourceLabel'].some(k=>typeof o[k]!=='string'||!(o[k] as string).length||(o[k] as string).length>500))return null;
 if(o.sourceUrl!==undefined&&(typeof o.sourceUrl!=='string'||!o.sourceUrl.startsWith('https://')))return null;
 if(!Array.isArray(o.stages)||!Array.isArray(o.relations))return null;
 const motions=['REVEAL_IN_ORDER','TRACE_SEQUENCE','TRACE_CYCLE','TRANSITION_FOCUS','EMPHASIZE_RELATION'];
 if(o.motion_intents!==undefined&&(!Array.isArray(o.motion_intents)||o.motion_intents.some(m=>typeof m!=='string'||!motions.includes(m))||new Set(o.motion_intents).size!==o.motion_intents.length||(o.topology==='sequence'&&o.motion_intents.includes('TRACE_CYCLE'))||(o.topology==='cycle'&&o.motion_intents.includes('TRACE_SEQUENCE'))))return null;
 const arts=['drop','filter','vessel','egg','larva','pupa','butterfly','idea','draft','review'];
 if(o.stages.some(s=>!s||typeof s!=='object'||Object.keys(s).sort().join(',')!=='art,detail,id,label'||['id','label','detail','art'].some(k=>typeof s[k]!=='string')||s.id.length>64||!arts.includes(s.art)))return null;
 if(o.relations.some(r=>!r||typeof r!=='object'||Object.keys(r).sort().join(',')!=='from,id,label,to'||['id','from','to','label'].some(k=>typeof r[k]!=='string')))return null;
 return validateProcess(o as ProcessScene)?o as ProcessScene:null;
}
