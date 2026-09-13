export const CUSTOM_CHANNEL = "lina-full-power-canvas-v1";

// Narrow Workspace panes need room for stacked controls as well as the representation.
// Preview and the real renderer share this viewport contract.
export function customVisualViewportHeight(width: number) {
  return width <= 520 ? 512 : 384;
}

export function customSandboxDocument(source: string, parameters: Record<string, string | number | boolean>, nonce: string, state: Record<string, string | null>) {
  const params = JSON.stringify(parameters).replace(/</g, "\\u003c");
  const initialState = JSON.stringify(state).replace(/</g, "\\u003c");
  const safeSource = source.replace(/<\/script/gi, "<\\/script");
  return `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><style>html,body,#root{height:100%;margin:0;box-sizing:border-box}body{overflow:auto}</style></head><body><main id="root"></main><script>
const activationBindings=new WeakMap();
const bridge={
  state:${initialState}, lastSelection:null, lastFocus:null, targetCounter:0, lastEvent:null,
  read:(id,fallback)=>{
    const value=bridge.state[id]; if(value==null)return fallback;
    if(typeof fallback==='string')return value;
    try {const parsed=JSON.parse(value);if(Array.isArray(fallback))return Array.isArray(parsed)?parsed:fallback;if(typeof parsed===typeof fallback)return parsed;}catch{}
    return fallback;
  },
  emit:(actionOrEvent,semanticId,detail={})=>{
    const event=typeof actionOrEvent==='object'&&actionOrEvent!==null
      ? {semantic_action:actionOrEvent.action,semantic_id:actionOrEvent.semantic_id,from_value:actionOrEvent.from_value??null,to_value:actionOrEvent.to_value??actionOrEvent.value??null}
      : {semantic_action:actionOrEvent,semantic_id:semanticId,from_value:detail.from_value??null,to_value:detail.to_value??detail.value??null};
    if(event.semantic_action==='SELECT'||event.semantic_action==='FOCUS'){
      event.from_value=null;event.to_value=null;
      if(event.semantic_action==='SELECT')bridge.lastSelection=event.semantic_id;else bridge.lastFocus=event.semantic_id;
    } else if(typeof event.to_value==='string') {
      event.from_value=event.from_value??bridge.state[event.semantic_id]??null;
      bridge.state[event.semantic_id]=event.to_value;
    }
    bridge.lastEvent=event;
    parent.postMessage({channel:'${CUSTOM_CHANNEL}',type:'EVENT',nonce:'${nonce}',...event},'*');
  },
  control:(element,id,action)=>{
    if(!element||typeof element.setAttribute!=='function')throw new Error('bridge.control requires an actual DOM element; bind after creating it.');
    const bound=element.getAttribute('data-semantic-id');if(bound&&bound!==id)throw new Error('A control element cannot represent two semantic IDs; bind the actual target objects.');
    element.setAttribute('data-semantic-id',id);element.setAttribute('data-canvas-action',[...new Set([...(element.getAttribute('data-canvas-action')||'').split(' ').filter(Boolean),action])].join(' '));
    return {
      read:(fallback)=>bridge.read(id,fallback),
      get selected(){return bridge.lastSelection===id;},
      emit:(value)=>bridge.emit(action,id,{to_value:value==null?null:typeof value==='string'?value:JSON.stringify(value)}),
      activate:(callback)=>{
        if(typeof callback!=='function')throw new Error('activate requires a callback');
        activationBindings.get(element)?.();
        const native=element.matches('button,input,select,textarea,a[href],summary');
        if(!native){if(!element.hasAttribute('role'))element.setAttribute('role','button');if(!element.hasAttribute('tabindex'))element.setAttribute('tabindex','0');}
        const click=e=>callback(e);
        const key=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();if(!e.repeat)callback(e);}};
        element.addEventListener('click',click);
        if(!native)element.addEventListener('keydown',key);
        activationBindings.set(element,()=>{element.removeEventListener('click',click);element.removeEventListener('keydown',key);});
      },
      drag:(handlers)=>{
        element.style.touchAction='none';element.draggable=false;element.setAttribute('data-canvas-gesture','drag');
        if(handlers.dropTarget){const target=typeof handlers.dropTarget==='string'?document.getElementById(handlers.dropTarget.replace(/^#/,'')):handlers.dropTarget;if(!target)throw new Error('drag dropTarget must be an existing DOM element or id');if(!target.id)target.id='canvas-drop-'+(++bridge.targetCounter);element.setAttribute('data-canvas-drop-target',target.id);}
        element.addEventListener('pointerdown',down=>{
          if(down.button!==0)return;down.preventDefault();element.focus?.();
          const capture=document.documentElement;capture.setPointerCapture(down.pointerId);
          const position=e=>({clientX:e.clientX,clientY:e.clientY,target:document.elementFromPoint(e.clientX,e.clientY)});
          const move=e=>{if(e.pointerId===down.pointerId)handlers.move?.(position(e));};
          const cleanup=()=>{document.removeEventListener('pointermove',move);document.removeEventListener('pointerup',end);document.removeEventListener('pointercancel',cancel);if(capture.hasPointerCapture(down.pointerId))capture.releasePointerCapture(down.pointerId);};
          const end=e=>{if(e.pointerId!==down.pointerId)return;cleanup();const previous=bridge.lastEvent;const value=handlers.end?.(position(e));if(value!==undefined){const serialized=typeof value==='string'?value:JSON.stringify(value);const latest=bridge.lastEvent;if(latest===previous||latest?.semantic_action!==action||latest?.semantic_id!==id||latest?.to_value!==serialized)bridge.emit(action,id,{to_value:serialized});}};
          const cancel=e=>{if(e.pointerId===down.pointerId)cleanup();};
          document.addEventListener('pointermove',move);document.addEventListener('pointerup',end);document.addEventListener('pointercancel',cancel);
        });
      }
    };
  }
};
const reportError=(error)=>parent.postMessage({diagnostic:String(error?.message??error?.reason?.message??'Runtime error').slice(0,180),channel:'${CUSTOM_CHANNEL}',type:'ERROR',nonce:'${nonce}',message:'Custom visual could not run.'},'*');
addEventListener('error',reportError);addEventListener('unhandledrejection',reportError);
try { ${safeSource}\nif(typeof window.mount!=='function')throw new Error('mount unavailable');window.mount(document.getElementById('root'),${params},bridge);parent.postMessage({channel:'${CUSTOM_CHANNEL}',type:'READY',nonce:'${nonce}'},'*'); } catch(error) { reportError(error); }
</script></body></html>`;
}
