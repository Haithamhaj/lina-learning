"use client";

import { type PointerEvent as ReactPointerEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type SentenceOrderingOperation,
  type SentenceOrderingState,
  type SentenceOrderingTokenId,
  makeReorderOperation,
  makeSubmitOperation,
} from "@/lib/studio/sentence-ordering";

type SentenceOrderingLabels = {
  eyebrow: string;
  title: string;
  instruction: string;
  sequenceLabel: string;
  moveEarlier: string;
  moveLater: string;
  submit: string;
  submitHint: string;
  pending: string;
  saved: string;
  invalid: string;
  dragging: string;
};

type Props = {
  sceneId: string;
  sceneVersion: number;
  state: SentenceOrderingState | null;
  locale: string;
  direction?: "ltr" | "rtl" | "auto";
  onOperation: (operation: SentenceOrderingOperation) => Promise<void>;
};

const english: SentenceOrderingLabels = {
  eyebrow: "Sentence ordering workspace",
  title: "Put these words into a sentence",
  instruction: "Move the English word tokens into the order you want, then submit your sentence.",
  sequenceLabel: "English word tokens",
  moveEarlier: "Move earlier",
  moveLater: "Move later",
  submit: "Check my sentence",
  submitHint: "The browser sends your chosen token order to Studio; it does not hold an answer key.",
  pending: "Saving your change…",
  saved: "Your action was sent to Studio.",
  invalid: "That action cannot be sent from this saved state.",
  dragging: "Moving",
};

const arabic: SentenceOrderingLabels = {
  eyebrow: "مساحة ترتيب الجملة",
  title: "رتّب هذه الكلمات في جملة",
  instruction: "حرّك كلمات اللغة الإنجليزية إلى الترتيب الذي تريده، ثم أرسل جملتك.",
  sequenceLabel: "كلمات إنجليزية مرتبة",
  moveEarlier: "حرّك إلى بداية الجملة",
  moveLater: "حرّك إلى نهاية الجملة",
  submit: "تحقّق من جملتي",
  submitHint: "يرسل المتصفح ترتيب الكلمات الذي اخترته إلى الاستوديو ولا يحتفظ بمفتاح إجابة.",
  pending: "يجري حفظ التغيير…",
  saved: "أُرسل الإجراء إلى الاستوديو.",
  invalid: "لا يمكن إرسال هذا الإجراء من هذه الحالة المحفوظة.",
  dragging: "يجري التحريك",
};

function labelsFor(locale: string): SentenceOrderingLabels {
  return locale.toLowerCase().startsWith("ar") ? arabic : english;
}

function resolvedDirection(locale: string, direction: Props["direction"]): "ltr" | "rtl" {
  if (direction === "ltr" || direction === "rtl") return direction;
  return locale.toLowerCase().startsWith("ar") ? "rtl" : "ltr";
}

export function SentenceOrderingWorkspace({ sceneId, sceneVersion, state, locale, direction = "auto", onOperation }: Props) {
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [draggedTokenId, setDraggedTokenId] = useState<SentenceOrderingTokenId | null>(null);
  const surfaceRef = useRef<HTMLElement | null>(null);
  const gestureRef = useRef<{ tokenId: SentenceOrderingTokenId; pointerId: number; target: HTMLDivElement } | null>(null);
  const labels = labelsFor(locale);
  const outerDir = resolvedDirection(locale, direction);
  const tokenById = new Map(state?.tokens.map((token) => [token.id, token]));
  const tokenLabel = (tokenId: SentenceOrderingTokenId) => tokenById.get(tokenId)?.text;

  const dispatch = async (operation: SentenceOrderingOperation | null) => {
    if (!operation || pending) {
      setFeedback(labels.invalid);
      return;
    }
    const focusedControl = document.activeElement instanceof HTMLElement
      ? document.activeElement.dataset.sentenceOrderingControl ?? null
      : null;
    setPending(true);
    setFeedback(labels.pending);
    try {
      await onOperation(operation);
      setFeedback(labels.saved);
    } catch {
      setFeedback(labels.invalid);
    } finally {
      setPending(false);
      if (focusedControl) {
        requestAnimationFrame(() => {
          const control = Array.from(document.querySelectorAll<HTMLElement>("[data-sentence-ordering-control]"))
            .find((candidate) => candidate.dataset.sentenceOrderingControl === focusedControl);
          if (control instanceof HTMLButtonElement && !control.disabled) control.focus();
        });
      }
    }
  };

  const reorder = (tokenId: SentenceOrderingTokenId, fromIndex: number, toIndex: number) => {
    if (!state) return;
    void dispatch(makeReorderOperation(
      state,
      sceneId,
      sceneVersion,
      tokenId,
      fromIndex,
      toIndex,
      `sentence-ordering-reorder:${crypto.randomUUID()}`,
    ));
  };

  const pickUp = (tokenId: SentenceOrderingTokenId, event: ReactPointerEvent<HTMLDivElement>) => {
    if (pending || gestureRef.current || !event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    gestureRef.current = { tokenId, pointerId: event.pointerId, target: event.currentTarget };
    setDraggedTokenId(tokenId);
  };

  const clearGesture = (pointerId: number) => {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== pointerId) return null;
    gestureRef.current = null;
    setDraggedTokenId(null);
    if (gesture.target.hasPointerCapture(pointerId)) gesture.target.releasePointerCapture(pointerId);
    return gesture;
  };

  const drop = (event: ReactPointerEvent<HTMLElement>) => {
    const gesture = clearGesture(event.pointerId);
    if (!gesture || !state) return;
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-sentence-ordering-token]");
    if (!target || !surfaceRef.current?.contains(target)) return;
    const targetTokenId = target.getAttribute("data-sentence-ordering-token") as SentenceOrderingTokenId | null;
    if (!targetTokenId || targetTokenId === gesture.tokenId) return;
    const fromIndex = state.token_ids.indexOf(gesture.tokenId);
    const toIndex = state.token_ids.indexOf(targetTokenId);
    if (fromIndex < 0 || toIndex < 0) return;
    reorder(gesture.tokenId, fromIndex, toIndex);
  };

  const submit = () => {
    if (!state) return;
    void dispatch(makeSubmitOperation(state, sceneId, sceneVersion, `sentence-ordering-submit:${crypto.randomUUID()}`));
  };

  if (!state) {
    return <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-950" dir={outerDir} role="status">{labels.invalid}</section>;
  }

  return (
    <section
      ref={surfaceRef}
      data-sentence-ordering-workspace
      onPointerUp={drop}
      onPointerCancel={(event) => { clearGesture(event.pointerId); }}
      onLostPointerCapture={(event) => { clearGesture(event.pointerId); }}
      className="rounded-[2rem] bg-[#f5f8ff] p-4 text-slate-900 shadow-sm ring-1 ring-indigo-100 sm:p-6"
      dir={outerDir}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-indigo-700">{labels.eyebrow}</p>
          <h1 className="mt-1 text-2xl font-black tracking-tight">{labels.title}</h1>
        </div>
        <p className="max-w-md text-sm leading-6 text-slate-600">{labels.instruction}</p>
      </div>

      <div data-sentence-ordering-token-surface className="mt-6" dir="ltr" lang="en">
        <p className="mb-3 text-sm font-semibold text-slate-700" id="sentence-ordering-token-label">{labels.sequenceLabel}</p>
        <div aria-labelledby="sentence-ordering-token-label" className="grid gap-3" role="list">
          {state.token_ids.map((tokenId, index) => {
            const token = tokenById.get(tokenId);
            if (!token) return null;
            const dragging = draggedTokenId === tokenId;
            return (
              <div
                key={tokenId}
                data-sentence-ordering-token={tokenId}
                onPointerDown={(event) => pickUp(tokenId, event)}
                className={`grid touch-none gap-3 rounded-2xl border bg-white p-4 shadow-sm sm:grid-cols-[auto_1fr_auto] sm:items-center ${dragging ? "border-indigo-400 ring-2 ring-indigo-200" : "border-indigo-100"}`}
                aria-label={`Word ${index + 1}. ${token.text}`}
                role="listitem"
              >
                <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-indigo-100 text-sm font-black text-indigo-800">{index + 1}</span>
                <span className="font-semibold leading-6">{token.text}</span>
                <span className="flex flex-wrap gap-2" onPointerDown={(event) => event.stopPropagation()}>
                  <Button type="button" variant="secondary" data-sentence-ordering-control={`${tokenId}:earlier`} aria-label={`${labels.moveEarlier}: ${token.text}`} className="motion-reduce:transition-none" disabled={pending || index === 0} onClick={() => reorder(tokenId, index, index - 1)}>
                    {labels.moveEarlier}
                  </Button>
                  <Button type="button" variant="secondary" data-sentence-ordering-control={`${tokenId}:later`} aria-label={`${labels.moveLater}: ${token.text}`} className="motion-reduce:transition-none" disabled={pending || index === state.token_ids.length - 1} onClick={() => reorder(tokenId, index, index + 1)}>
                    {labels.moveLater}
                  </Button>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <p className="mt-4 text-sm text-slate-600" role="status">{draggedTokenId ? `${labels.dragging}: ${tokenLabel(draggedTokenId) ?? ""}` : labels.instruction}</p>
      <div className="mt-5 border-t border-indigo-100 pt-4">
        <Button type="button" data-sentence-ordering-control="submit" className="motion-reduce:transition-none" disabled={pending} onClick={submit}>{labels.submit}</Button>
        <p className="mt-2 text-sm text-slate-600">{labels.submitHint}</p>
        {feedback ? <p className="mt-2 text-sm font-semibold text-slate-800" role="status" aria-live="polite">{feedback}</p> : null}
      </div>
    </section>
  );
}
