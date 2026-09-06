"use client";

import { type PointerEvent as ReactPointerEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type ArabicSentenceOrderingOperation,
  type ArabicSentenceOrderingState,
  type ArabicSentenceOrderingTokenId,
  makeArabicReorderOperation,
  makeArabicSubmitOperation,
} from "@/lib/studio/arabic-sentence-ordering";

type Props = { sceneId: string; sceneVersion: number; state: ArabicSentenceOrderingState | null; onOperation: (operation: ArabicSentenceOrderingOperation) => Promise<void> };

export function ArabicSentenceOrderingWorkspace({ sceneId, sceneVersion, state, onOperation }: Props) {
  const [pending, setPending] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [draggedTokenId, setDraggedTokenId] = useState<ArabicSentenceOrderingTokenId | null>(null);
  const surfaceRef = useRef<HTMLElement | null>(null);
  const gestureRef = useRef<{ tokenId: ArabicSentenceOrderingTokenId; pointerId: number; target: HTMLLIElement } | null>(null);
  const tokenById = new Map(state?.tokens.map((token) => [token.id, token]));

  const dispatch = async (operation: ArabicSentenceOrderingOperation | null) => {
    if (!operation || pending) { setStatus("لا يمكن إرسال هذا الإجراء من الحالة المحفوظة."); return; }
    const focusedControl = document.activeElement instanceof HTMLElement ? document.activeElement.dataset.arabicOrderingControl ?? null : null;
    setPending(true); setStatus("يجري حفظ التغيير…");
    try { await onOperation(operation); setStatus("أُرسل الإجراء إلى الاستوديو."); }
    catch { setStatus("تعذّر حفظ الإجراء. أُعيدت الحالة المعتمدة."); }
    finally {
      setPending(false);
      if (focusedControl) requestAnimationFrame(() => {
        const control = Array.from(document.querySelectorAll<HTMLElement>("[data-arabic-ordering-control]"))
          .find((candidate) => candidate.dataset.arabicOrderingControl === focusedControl);
        if (control instanceof HTMLButtonElement && !control.disabled) control.focus();
        else {
          const tokenId = focusedControl.split(":")[0];
          const fallback = Array.from(surfaceRef.current?.querySelectorAll<HTMLButtonElement>("button[data-arabic-ordering-control]") ?? [])
            .find(candidate => !candidate.disabled && candidate.dataset.arabicOrderingControl?.startsWith(`${tokenId}:`))
            ?? surfaceRef.current?.querySelector<HTMLButtonElement>('button[data-arabic-ordering-control="submit"]');
          fallback?.focus();
        }
      });
    }
  };

  const reorder = (tokenId: ArabicSentenceOrderingTokenId, fromIndex: number, toIndex: number) => {
    if (!state) return;
    void dispatch(makeArabicReorderOperation(state, sceneId, sceneVersion, tokenId, fromIndex, toIndex, `arabic-ordering-reorder:${crypto.randomUUID()}`));
  };
  const pickUp = (tokenId: ArabicSentenceOrderingTokenId, event: ReactPointerEvent<HTMLLIElement>) => {
    if (pending || gestureRef.current || !event.isPrimary || event.button !== 0) return;
    event.preventDefault(); event.currentTarget.setPointerCapture(event.pointerId);
    gestureRef.current = { tokenId, pointerId: event.pointerId, target: event.currentTarget }; setDraggedTokenId(tokenId);
  };
  const clearGesture = (pointerId: number) => {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== pointerId) return null;
    gestureRef.current = null; setDraggedTokenId(null);
    if (gesture.target.hasPointerCapture(pointerId)) gesture.target.releasePointerCapture(pointerId);
    return gesture;
  };
  const drop = (event: ReactPointerEvent<HTMLElement>) => {
    const gesture = clearGesture(event.pointerId);
    if (!gesture || !state) return;
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-arabic-ordering-token]");
    if (!target || !surfaceRef.current?.contains(target)) return;
    const targetId = target.getAttribute("data-arabic-ordering-token") as ArabicSentenceOrderingTokenId | null;
    if (!targetId || targetId === gesture.tokenId) return;
    const fromIndex = state.token_ids.indexOf(gesture.tokenId); const toIndex = state.token_ids.indexOf(targetId);
    if (fromIndex < 0 || toIndex < 0) return;
    reorder(gesture.tokenId, fromIndex, toIndex);
  };

  if (!state) return <section dir="rtl" lang="ar" role="status" className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-rose-950">لا يمكن فتح نشاط اللغة العربية من الحالة المحفوظة.</section>;
  return <section ref={surfaceRef} dir="rtl" lang="ar" onPointerUp={drop} onPointerCancel={(event) => { clearGesture(event.pointerId); }} onLostPointerCapture={(event) => { clearGesture(event.pointerId); }} className="rounded-[2rem] bg-[#fffaf0] p-4 text-slate-900 shadow-sm ring-1 ring-orange-100 sm:p-6">
    <p className="text-xs font-bold text-orange-600">مساحة ترتيب الجملة العربية</p><h3 className="mt-1 text-2xl font-black">رتّب الكلمات في جملة تبدأ بالفعل</h3><p className="mt-2 leading-6">رتّب الكلمات لتكوين الجملة التي تبدأ بالفعل وتصف أن الطالبة تكتب الدرس.</p>
    <ol aria-label="كلمات الجملة العربية" className="mt-5 grid gap-3">{state.token_ids.map((id, index) => {
      const token = tokenById.get(id); if (!token) return null; const dragging = draggedTokenId === id;
      return <li key={id} data-arabic-ordering-token={id} onPointerDown={(event) => pickUp(id, event)} role="listitem" aria-label={`${index + 1}. ${token.text}`} className={`grid touch-none gap-3 rounded-2xl bg-white p-3 ring-1 shadow-sm sm:grid-cols-[auto_1fr_auto] sm:items-center ${dragging ? "ring-2 ring-orange-300" : "ring-slate-200"}`}>
        <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-orange-100 text-sm font-black text-orange-800">{index + 1}</span><span className="font-semibold" dir="rtl">{token.text}</span>
        <span className="flex flex-wrap gap-2" onPointerDown={(event) => event.stopPropagation()}><Button type="button" variant="secondary" data-arabic-ordering-control={`${id}:earlier`} aria-label={`حرّك للأمام: ${token.text}`} disabled={pending || index === 0} onClick={() => reorder(id, index, index - 1)}>حرّك للأمام</Button><Button type="button" variant="secondary" data-arabic-ordering-control={`${id}:later`} aria-label={`حرّك للخلف: ${token.text}`} disabled={pending || index === state.token_ids.length - 1} onClick={() => reorder(id, index, index + 1)}>حرّك للخلف</Button></span>
      </li>;
    })}</ol>
    <p className="mt-4 text-sm text-slate-600" role="status" aria-live="polite">{draggedTokenId ? `يجري تحريك: ${tokenById.get(draggedTokenId)?.text ?? ""}` : status ?? "اسحب كلمة إلى كلمة أخرى أو استخدم أزرار التحريك."}</p>
    <div className="mt-5 border-t border-orange-100 pt-4"><Button type="button" data-arabic-ordering-control="submit" disabled={pending} onClick={() => void dispatch(makeArabicSubmitOperation(state, sceneId, sceneVersion, `arabic-ordering-submit:${crypto.randomUUID()}`))}>تحقّق من ترتيبي</Button></div>
  </section>;
}
