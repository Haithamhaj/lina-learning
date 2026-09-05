"use client";

import { type PointerEvent as ReactPointerEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type MakeTenGroupId,
  type MakeTenOperation,
  type MakeTenState,
  groupForItem,
  makeSubmitOperation,
  makeTransferOperation,
  otherGroup,
} from "@/lib/studio/make-ten";

type MakeTenLabels = {
  title: string;
  instruction: string;
  tenFrame: string;
  onesGroup: string;
  moveTo: string;
  submit: string;
  submitHint: string;
  pending: string;
  saved: string;
  invalid: string;
  dragged: string;
};

type Props = {
  sceneId: string;
  sceneVersion: number;
  state: MakeTenState | null;
  locale: string;
  direction?: "ltr" | "rtl" | "auto";
  onOperation: (operation: MakeTenOperation) => Promise<void>;
};

const english: MakeTenLabels = {
  title: "Make a ten",
  instruction: "Move one counter from the group of 6 into the ten-frame. Then submit what you made.",
  tenFrame: "Ten frame",
  onesGroup: "Group of ones",
  moveTo: "Move to",
  submit: "Check my groups",
  submitHint: "The check uses the saved Studio state, not a browser calculation.",
  pending: "Saving your move…",
  saved: "Your action was sent to Studio.",
  invalid: "That action cannot be sent from this saved state.",
  dragged: "Ready to move",
};

const arabic: MakeTenLabels = {
  title: "كوِّن عشرة",
  instruction: "انقل عدادًا واحدًا من مجموعة الـ٦ إلى إطار العشرة، ثم أرسل ترتيبك للتحقق.",
  tenFrame: "إطار العشرة",
  onesGroup: "مجموعة الآحاد",
  moveTo: "انقل إلى",
  submit: "تحقق من مجموعاتي",
  submitHint: "التحقق يستخدم حالة الاستوديو المحفوظة، وليس عملية حسابية في المتصفح.",
  pending: "يجري حفظ الحركة…",
  saved: "أُرسل الإجراء إلى الاستوديو.",
  invalid: "لا يمكن إرسال هذا الإجراء من هذه الحالة المحفوظة.",
  dragged: "جاهز للنقل",
};

function labelsFor(locale: string): MakeTenLabels {
  return locale.toLowerCase().startsWith("ar") ? arabic : english;
}

function resolvedDirection(locale: string, direction: Props["direction"]): "ltr" | "rtl" {
  if (direction === "rtl" || direction === "ltr") return direction;
  return locale.toLowerCase().startsWith("ar") ? "rtl" : "ltr";
}

function itemNumber(itemId: string): string {
  return String(Number(itemId.slice(-2)));
}

function GroupBoard({
  groupId,
  title,
  itemIds,
  draggedItemId,
  onPickUp,
}: {
  groupId: MakeTenGroupId;
  title: string;
  itemIds: string[];
  draggedItemId: string | null;
  onPickUp: (itemId: string, event: ReactPointerEvent<SVGCircleElement>) => void;
}) {
  const slots = Array.from({ length: groupId === "ten-frame" ? 10 : 6 });
  return (
    <section
      aria-label={title}
      data-make-ten-group={groupId}
      className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="font-bold text-slate-900">{title}</h2>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-700">{itemIds.length}</span>
      </div>
      <svg viewBox="0 0 300 138" className="h-auto w-full" style={{ touchAction: "none" }} role="img" aria-label={`${title}: ${itemIds.length}`}>
        {slots.map((_, index) => {
          const itemId = itemIds[index];
          const x = 35 + (index % 5) * 58;
          const y = 42 + Math.floor(index / 5) * 58;
          return (
            <g key={`${groupId}-${index}`}>
              <rect x={x - 22} y={y - 22} width="44" height="44" rx="10" fill="#f8fafc" stroke="#cbd5e1" />
              {itemId ? (
                <circle
                  data-make-ten-item={itemId}
                  cx={x}
                  cy={y}
                  r="16"
                  fill={draggedItemId === itemId ? "#f59e0b" : "#2563eb"}
                  onPointerDown={(event) => onPickUp(itemId, event)}
                />
              ) : null}
              {itemId ? <text x={x} y={y + 5} textAnchor="middle" fill="white" fontSize="12" fontWeight="700" pointerEvents="none">{itemNumber(itemId)}</text> : null}
            </g>
          );
        })}
      </svg>
    </section>
  );
}

export function TenFrameGroupTransfer({ sceneId, sceneVersion, state, locale, direction = "auto", onOperation }: Props) {
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null);
  const surfaceRef = useRef<HTMLElement | null>(null);
  const gestureRef = useRef<{ itemId: string; pointerId: number; target: SVGCircleElement } | null>(null);
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const labels = labelsFor(locale);
  const dir = resolvedDirection(locale, direction);

  const dispatch = async (operation: MakeTenOperation | null) => {
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

  const transfer = (itemId: string) => {
    if (!state) return;
    void dispatch(makeTransferOperation(state, sceneId, sceneVersion, itemId, `make-ten-transfer:${crypto.randomUUID()}`));
  };

  const pickUp = (itemId: string, event: ReactPointerEvent<SVGCircleElement>) => {
    if (pending || gestureRef.current || !event.isPrimary || event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    gestureRef.current = { itemId, pointerId: event.pointerId, target: event.currentTarget };
    setDraggedItemId(itemId);
  };

  const clearGesture = (pointerId: number) => {
    const gesture = gestureRef.current;
    if (!gesture || gesture.pointerId !== pointerId) return null;
    // Clear before releasing capture: normal lost-capture must not undo a drop.
    gestureRef.current = null;
    setDraggedItemId(null);
    if (gesture.target.hasPointerCapture(pointerId)) gesture.target.releasePointerCapture(pointerId);
    return gesture;
  };

  const drop = (event: ReactPointerEvent<HTMLElement>) => {
    const gesture = clearGesture(event.pointerId);
    if (!gesture || !state) return;
    // Captured pointerup targets the source; hit-test only within this activity.
    const board = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-make-ten-group]");
    if (!board || !surfaceRef.current?.contains(board)) return;
    const groupId = board.getAttribute("data-make-ten-group");
    if (groupId !== "ten-frame" && groupId !== "ones-group") return;
    if (groupForItem(state, gesture.itemId) === groupId) return;
    transfer(gesture.itemId);
  };

  const submit = () => {
    if (!state) return;
    void dispatch(makeSubmitOperation(state, sceneId, sceneVersion, `make-ten-submit:${crypto.randomUUID()}`));
  };

  if (!state) {
    return <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 text-amber-950" dir={dir} role="status">{labels.invalid}</section>;
  }

  const groups: MakeTenGroupId[] = dir === "rtl" ? ["ones-group", "ten-frame"] : ["ten-frame", "ones-group"];
  return (
    <section ref={surfaceRef} onPointerUp={drop} onPointerCancel={(event) => { clearGesture(event.pointerId); }} onLostPointerCapture={(event) => { clearGesture(event.pointerId); }} className="rounded-[2rem] bg-[#fffaf0] p-4 text-slate-900 shadow-sm ring-1 ring-orange-100 sm:p-6" dir={dir}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-orange-600">Make-Ten Group Transfer</p>
          <h1 className="mt-1 text-2xl font-black tracking-tight">{labels.title}</h1>
        </div>
        <p className="max-w-md text-sm leading-6 text-slate-600">{labels.instruction}</p>
      </div>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {groups.map((groupId) => (
          <GroupBoard
            key={groupId}
            groupId={groupId}
            title={groupId === "ten-frame" ? labels.tenFrame : labels.onesGroup}
            itemIds={state.groups[groupId].item_ids}
            draggedItemId={draggedItemId}
            onPickUp={pickUp}
          />
        ))}
      </div>
      <p className="mt-3 text-sm text-slate-600" role="status">{draggedItemId ? `${labels.dragged}: ${itemNumber(draggedItemId)}` : labels.instruction}</p>
      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {(["ten-frame", "ones-group"] as MakeTenGroupId[]).flatMap((groupId) => state.groups[groupId].item_ids.map((itemId) => (
          <Button key={itemId} type="button" variant="secondary" className="motion-reduce:transition-none" disabled={pending} onClick={() => transfer(itemId)}>
            {labels.moveTo} {otherGroup(groupId) === "ten-frame" ? labels.tenFrame : labels.onesGroup}: {itemNumber(itemId)}
          </Button>
        )))}
      </div>
      <div className="mt-5 border-t border-orange-100 pt-4">
        <Button type="button" className="motion-reduce:transition-none" disabled={pending} onClick={submit}>{labels.submit}</Button>
        <p className="mt-2 text-sm text-slate-600">{labels.submitHint}</p>
        {feedback ? <p className="mt-2 text-sm font-semibold text-slate-800" role="status" aria-live="polite">{feedback}</p> : null}
      </div>
    </section>
  );
}
