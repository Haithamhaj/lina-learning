"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

import { TenFrameGroupTransfer } from "@/components/studio/ten-frame-group-transfer";
import {
  type MakeTenOperation,
  applyMockMakeTenOperation,
  makeTenReviewState,
} from "@/lib/studio/make-ten";

/**
 * Isolated review seam for the real production renderer. It intentionally
 * labels its local controller as a mock and does not open, mutate, or replace
 * any Student route or Studio server state.
 */
function MakeTenReviewContent() {
  const searchParams = useSearchParams();
  const [state, setState] = useState(makeTenReviewState);
  const [sceneVersion, setSceneVersion] = useState(2);
  const [lastOperation, setLastOperation] = useState<MakeTenOperation | null>(null);
  const [operationTrace, setOperationTrace] = useState<MakeTenOperation[]>([]);
  const locale = searchParams.get("locale") === "ar" ? "ar" : "en";
  const requestedDirection = searchParams.get("direction");
  const direction = requestedDirection === "ltr" || requestedDirection === "rtl" ? requestedDirection : "auto";
  const rejectOperation = searchParams.get("reject_operation") === "1";

  const acceptMockOperation = async (operation: MakeTenOperation) => {
    setOperationTrace((current) => [...current, operation]);
    setLastOperation(operation);
    if (rejectOperation) throw new Error("Mock rejection for renderer review.");
    setState((current) => applyMockMakeTenOperation(current, operation));
    setSceneVersion((current) => current + 1);
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-6 sm:px-8 sm:py-10">
      <div className="mx-auto max-w-4xl">
        <p className="mb-4 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
          Isolated review mount · mock Studio Snapshot/controller · not a Student route or persistence claim.
        </p>
        <output data-operation-trace={JSON.stringify(operationTrace)} className="mb-4 block break-words rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700" aria-live="polite">
          Mock operation trace: {lastOperation === null ? "none" : JSON.stringify(lastOperation)}
        </output>
        <TenFrameGroupTransfer
          sceneId="review-make-ten-scene"
          sceneVersion={sceneVersion}
          state={state}
          locale={locale}
          direction={direction}
          onOperation={acceptMockOperation}
        />
      </div>
    </main>
  );
}

export default function MakeTenReviewPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-100" aria-busy="true" />}>
      <MakeTenReviewContent />
    </Suspense>
  );
}
