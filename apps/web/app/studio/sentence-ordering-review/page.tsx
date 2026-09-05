"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { SentenceOrderingWorkspace } from "@/components/studio/sentence-ordering-workspace";
import {
  type SentenceOrderingOperation,
  type SentenceOrderingState,
  applyMockSentenceOrderingOperation,
  sentenceOrderingReviewState,
} from "@/lib/studio/sentence-ordering";

declare global {
  interface Window {
    __LINA_SENTENCE_ORDERING_REVIEW_SCENE__?: SentenceOrderingState;
  }
}

/** Isolated mock mount for renderer and browser review; it has no Student-route or persistence authority. */
function SentenceOrderingReviewContent() {
  const searchParams = useSearchParams();
  const [state, setState] = useState(sentenceOrderingReviewState);
  const [sceneVersion, setSceneVersion] = useState(2);
  const [lastOperation, setLastOperation] = useState<SentenceOrderingOperation | null>(null);
  const [operationTrace, setOperationTrace] = useState<SentenceOrderingOperation[]>([]);
  const locale = searchParams.get("locale") === "ar" ? "ar" : "en";
  const requestedDirection = searchParams.get("direction");
  const direction = requestedDirection === "ltr" || requestedDirection === "rtl" ? requestedDirection : "auto";
  const rejectOperation = searchParams.get("reject_operation") === "1";

  useEffect(() => {
    window.__LINA_SENTENCE_ORDERING_REVIEW_SCENE__ = state;
    return () => { delete window.__LINA_SENTENCE_ORDERING_REVIEW_SCENE__; };
  }, [state]);

  const acceptMockOperation = async (operation: SentenceOrderingOperation) => {
    setOperationTrace((current) => [...current, operation]);
    setLastOperation(operation);
    if (rejectOperation) throw new Error("Mock rejection for renderer review.");
    setState((current) => applyMockSentenceOrderingOperation(current, operation));
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
        <SentenceOrderingWorkspace
          sceneId="review-sentence-ordering-scene"
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

export default function SentenceOrderingReviewPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-100" aria-busy="true" />}>
      <SentenceOrderingReviewContent />
    </Suspense>
  );
}
