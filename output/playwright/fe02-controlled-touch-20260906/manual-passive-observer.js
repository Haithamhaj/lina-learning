// Manual verification only. Paste into the inspected Lina page console once.
// Records input; never dispatches events, intercepts handlers, or changes app state.
(() => {
  if (globalThis.__fe02TouchObserver) throw new Error("Observer already installed");
  const trace = [];
  const types = ["pointerdown", "pointermove", "pointerup", "pointercancel",
    "gotpointercapture", "lostpointercapture", "touchstart", "touchmove", "touchend", "touchcancel"];
  const record = (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const item = target?.closest("[data-make-ten-item], [data-sentence-ordering-token], [data-process-sequence-stage]");
    const points = "changedTouches" in event
      ? Array.from(event.changedTouches).map(t => ({ id: t.identifier, x: t.clientX, y: t.clientY }))
      : [];
    trace.push({
      type: event.type, pointerType: event.pointerType ?? null, isTrusted: event.isTrusted,
      pointerId: event.pointerId ?? null, timeStamp: event.timeStamp,
      x: event.clientX ?? null, y: event.clientY ?? null,
      targetTag: target?.tagName ?? null,
      itemId: item?.getAttribute("data-make-ten-item") ?? item?.getAttribute("data-sentence-ordering-token")
        ?? item?.getAttribute("data-process-sequence-stage") ?? null,
      points
    });
  };
  for (const type of types) document.addEventListener(type, record, {capture:true, passive:true});
  globalThis.__fe02TouchObserver = {
    trace,
    stop() {
      for (const type of types) document.removeEventListener(type, record, true);
      delete globalThis.__fe02TouchObserver;
    }
  };
  return "Passive observer installed; no gesture dispatched";
})();
