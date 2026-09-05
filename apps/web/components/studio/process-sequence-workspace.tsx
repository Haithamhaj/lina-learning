"use client";

import { type PointerEvent as ReactPointerEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type ProcessSequenceOperation,
  type ProcessSequenceStageId,
  type ProcessSequenceState,
  makeReorderOperation,
  makeSubmitOperation,
} from "@/lib/studio/process-sequence";

type ProcessSequenceLabels = {
  eyebrow: string;
  title: string;
  instruction: string;
  moveUp: string;
  moveDown: string;
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
  state: ProcessSequenceState | null;
  locale: string;
  direction?: "ltr" | "rtl" | "auto";
  onOperation: (operation: ProcessSequenceOperation) => Promise<void>;
};

const english: ProcessSequenceLabels = {
  eyebrow: "Process sequence workspace",
  title: "Put the filtration steps in order",
  instruction: "Move the named steps into a process order, then submit what you arranged.",
  moveUp: "Move up",
  moveDown: "Move down",
  submit: "Check my sequence",
  submitHint: "The check uses saved Studio state, not a browser answer key.",
  pending: "Saving your change…",
  saved: "Your action was sent to Studio.",
  invalid: "That action cannot be sent from this saved state.",
  dragging: "Moving",
};

const arabic: ProcessSequenceLabels = {
  eyebrow: "مساحة ترتيب الخطوات",
  title: "رتّب خطوات الترشيح",
  instruction: "حرّك الخطوات المسمّاة إلى ترتيب عملي، ثم أرسل ما رتّبته.",
  moveUp: "حرّك للأعلى",
  moveDown: "حرّك للأسفل",
  submit: "تحقّق من ترتيبي",
  submitHint: "يعتمد التحقّق على حالة الاستوديو المحفوظة، وليس مفتاح إجابة في المتصفح.",
  pending: "يجري حفظ التغيير…",
  saved: "أُرسل الإجراء إلى الاستوديو.",
  invalid: "لا يمكن إرسال هذا الإجراء من هذه الحالة المحفوظة.",
  dragging: "يجري التحريك",
};

function labelsFor(locale: string): ProcessSequenceLabels {
  return locale.toLowerCase().startsWith("ar") ? arabic : english;
}

function resolvedDirection(locale: string, direction: Props["direction"]): "ltr" | "rtl" {
  if (direction === "ltr" || direction === "rtl") return direction;
  return locale.toLowerCase().startsWith("ar") ? "rtl" : "ltr";
}

export function ProcessSequenceWorkspace({ sceneId, sceneVersion, state, locale, direction = "auto", onOperation }: Props) {
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [draggedStageId, setDraggedStageId] = useState<ProcessSequenceStageId | null>(null);
  const surfaceRef = useRef<HTMLElement | null>(null);
  const gestureRef = useRef<{ stageId: ProcessSequenceStageId; pointerId: number; target: HTMLLIElement } | null>(null);
  const labels = labelsFor(locale);
  const dir = resolvedDirection(locale, direction);
  const stageById = new Map(state?.stages.map((stage) => [stage.id, stage]));
  const stageLabel = (stageId: ProcessSequenceStageId) => {
    const stage = stageById.get(stageId);
    return locale.toLowerCase().startsWith("ar") ? stage?.label_ar : stage?.label_en;
  };

  const dispatch = async (operation: ProcessSequenceOperation | null) => {
    if (!operation || pending) {
      setFeedback(labels.invalid);
      return;
    }
    setPending(true);
    setFeedback(labels.pending);
    try {
      await onOperation(operation);
      setFeedback(labels.saved);
    } catch {
      setFeedback(labels.invalid);
    } finally {
      setPending(false);
    }
  };

  const reorder = (stageId: ProcessSequenceStageId, fromIndex: number, toIndex: number) => {
    if (!state) return;
    void dispatch(makeReorderOperation(
      state,
      sceneId,
      sceneVersion,
      stageId,
      fromIndex,
      toIndex,
      `process-sequence-reorder:${crypto.randomUUID()}`,
    ));
  };

  const pickUp = (stageId: ProcessSequenceStageId, event: ReactPointerEvent<HTMLLIElement>) => {
    if (pending || gestureRef.current || !event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    gestureRef.current = { stageId, pointerId: event.pointerId, target: event.currentTarget };
    setDraggedStageId(stageId);
  };

  const clearGesture = (pointerId: number) => {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== pointerId) return null;
    gestureRef.current = null;
    setDraggedStageId(null);
    if (gesture.target.hasPointerCapture(pointerId)) gesture.target.releasePointerCapture(pointerId);
    return gesture;
  };

  const drop = (event: ReactPointerEvent<HTMLElement>) => {
    const gesture = clearGesture(event.pointerId);
    if (!gesture || !state) return;
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-process-sequence-stage]");
    if (!target || !surfaceRef.current?.contains(target)) return;
    const targetStageId = target.getAttribute("data-process-sequence-stage") as ProcessSequenceStageId | null;
    if (!targetStageId || targetStageId === gesture.stageId) return;
    const fromIndex = state.stage_ids.indexOf(gesture.stageId);
    const toIndex = state.stage_ids.indexOf(targetStageId);
    if (fromIndex < 0 || toIndex < 0) return;
    reorder(gesture.stageId, fromIndex, toIndex);
  };

  const submit = () => {
    if (!state) return;
    void dispatch(makeSubmitOperation(state, sceneId, sceneVersion, `process-sequence-submit:${crypto.randomUUID()}`));
  };

  if (!state) {
    return <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-950" dir={dir} role="status">{labels.invalid}</section>;
  }

  return (
    <section
      ref={surfaceRef}
      onPointerUp={drop}
      onPointerCancel={(event) => { clearGesture(event.pointerId); }}
      onLostPointerCapture={(event) => { clearGesture(event.pointerId); }}
      className="rounded-[2rem] bg-[#effbf7] p-4 text-slate-900 shadow-sm ring-1 ring-emerald-100 sm:p-6"
      dir={dir}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">{labels.eyebrow}</p>
          <h1 className="mt-1 text-2xl font-black tracking-tight">{labels.title}</h1>
        </div>
        <p className="max-w-md text-sm leading-6 text-slate-600">{labels.instruction}</p>
      </div>
      <ol className="mt-6 grid gap-3" aria-label={labels.title}>
        {state.stage_ids.map((stageId, index) => {
          const stage = stageById.get(stageId);
          if (!stage) return null;
          const label = stageLabel(stageId);
          const dragging = draggedStageId === stageId;
          return (
            <li
              key={stageId}
              data-process-sequence-stage={stageId}
              onPointerDown={(event) => pickUp(stageId, event)}
              className={`grid touch-none gap-3 rounded-2xl border bg-white p-4 shadow-sm sm:grid-cols-[auto_1fr_auto] sm:items-center ${dragging ? "border-emerald-400 ring-2 ring-emerald-200" : "border-emerald-100"}`}
              aria-label={`${index + 1}. ${label}`}
            >
              <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-emerald-100 text-sm font-black text-emerald-800">{index + 1}</span>
              <span className="font-semibold leading-6">{label}</span>
              <span className="flex flex-wrap gap-2" onPointerDown={(event) => event.stopPropagation()}>
                <Button type="button" variant="secondary" className="motion-reduce:transition-none" disabled={pending || index === 0} onClick={() => reorder(stageId, index, index - 1)}>
                  {labels.moveUp}
                </Button>
                <Button type="button" variant="secondary" className="motion-reduce:transition-none" disabled={pending || index === state.stage_ids.length - 1} onClick={() => reorder(stageId, index, index + 1)}>
                  {labels.moveDown}
                </Button>
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 text-sm text-slate-600" role="status">{draggedStageId ? `${labels.dragging}: ${stageLabel(draggedStageId) ?? ""}` : labels.instruction}</p>
      <div className="mt-5 border-t border-emerald-100 pt-4">
        <Button type="button" className="motion-reduce:transition-none" disabled={pending} onClick={submit}>{labels.submit}</Button>
        <p className="mt-2 text-sm text-slate-600">{labels.submitHint}</p>
        {feedback ? <p className="mt-2 text-sm font-semibold text-slate-800" role="status" aria-live="polite">{feedback}</p> : null}
      </div>
    </section>
  );
}
