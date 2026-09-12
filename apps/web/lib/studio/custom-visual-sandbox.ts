export const CUSTOM_CHANNEL = "lina-full-power-canvas-v1";

export function customSandboxDocument(source: string, parameters: Record<string, string | number | boolean>, nonce: string, state: Record<string, string | null>) {
  const params = JSON.stringify(parameters).replace(/</g, "\\u003c");
  const initialState = JSON.stringify(state).replace(/</g, "\\u003c");
  const safeSource = source.replace(/<\/script/gi, "<\\/script");
  return `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><style>html,body,#root{height:100%;margin:0;box-sizing:border-box}body{overflow:auto}</style></head><body><main id="root"></main><script>
const bridge={state:${initialState},emit:(actionOrEvent,semanticId,detail={})=>{const event=typeof actionOrEvent==='object'&&actionOrEvent!==null?{semantic_action:actionOrEvent.action,semantic_id:actionOrEvent.semantic_id,from_value:actionOrEvent.from_value??null,to_value:actionOrEvent.to_value??actionOrEvent.value??null}:{semantic_action:actionOrEvent,semantic_id:semanticId,from_value:detail.from_value??null,to_value:detail.to_value??null};parent.postMessage({channel:'${CUSTOM_CHANNEL}',type:'EVENT',nonce:'${nonce}',...event},'*')}};
try { ${safeSource}\nif(typeof window.mount!=='function')throw new Error('mount unavailable');window.mount(document.getElementById('root'),${params},bridge);parent.postMessage({channel:'${CUSTOM_CHANNEL}',type:'READY',nonce:'${nonce}'},'*'); } catch(error) { parent.postMessage({channel:'${CUSTOM_CHANNEL}',type:'ERROR',nonce:'${nonce}',message:'Custom visual could not start.'},'*'); }
</script></body></html>`;
}
