"use client";

import { ProcessSequenceWorkspace } from "@/components/studio/process-sequence-workspace";
import { ArabicSentenceOrderingWorkspace } from "@/components/studio/arabic-sentence-ordering-workspace";
import { SentenceOrderingWorkspace } from "@/components/studio/sentence-ordering-workspace";
import { TenFrameGroupTransfer } from "@/components/studio/ten-frame-group-transfer";
import { DecimalNumberLineWorkspace } from "@/components/studio/decimal-number-line-workspace";
import { readDecimalLineState } from "@/lib/studio/decimal-number-line";
import type { StudioOperation, StudioSnapshotFrame } from "@/lib/studio/contracts";
import { readMakeTenState } from "@/lib/studio/make-ten";
import { readArabicSentenceOrderingState } from "@/lib/studio/arabic-sentence-ordering";
import { readProcessSequenceState } from "@/lib/studio/process-sequence";
import { activeSceneRendererState, resolveApprovedStudioRenderer } from "@/lib/studio/renderer-host";
import { readSentenceOrderingState } from "@/lib/studio/sentence-ordering";

type Props = {
  snapshot: StudioSnapshotFrame;
  operationPending: boolean;
  onOperation: (operation: StudioOperation) => Promise<void>;
  onReload: () => void;
};

function WorkspaceError({ onReload }: Pick<Props, "onReload">) {
  return (
    <section className="rounded-[1.75rem] border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900" role="alert">
      <p className="font-bold">This learning workspace could not be opened safely.</p>
      <p className="mt-2 leading-6">Your Tutor chat is still available. Reload the Workspace to use the server’s current Studio state.</p>
      <button className="mt-4 rounded-xl bg-white px-3 py-2 font-semibold text-rose-900 ring-1 ring-rose-200 hover:bg-rose-100 focus:outline-none focus:ring-2 focus:ring-rose-500" type="button" onClick={onReload}>Reload Workspace</button>
    </section>
  );
}

/** Renders only an active, exact accepted Scene; absent Scene means no Workspace. */
export function StudioRendererHost({ snapshot, operationPending, onOperation, onReload }: Props) {
  const scene = snapshot.active_scene_contract;
  if (scene === null) return null;
  const renderer = resolveApprovedStudioRenderer(scene);
  if (renderer === null || operationPending) {
    if (renderer === null) return <WorkspaceError onReload={onReload} />;
  }

  const onApprovedOperation = async (operation: StudioOperation) => {
    if (operationPending) throw new Error("A Studio operation is already pending.");
    await onOperation(operation);
  };
  const state = activeSceneRendererState(snapshot);

  if (renderer === "MATH_DECIMAL_NUMBER_LINE") {
    return <DecimalNumberLineWorkspace sceneId={scene.scene_id} sceneVersion={scene.scene_version} state={readDecimalLineState(state)} locale={scene.locale} onOperation={onApprovedOperation} onReload={onReload} />;
  }

  if (renderer === "MATH_MAKE_TEN") {
    return <TenFrameGroupTransfer sceneId={scene.scene_id} sceneVersion={scene.scene_version} state={readMakeTenState(state)} locale={scene.locale} direction={scene.direction} onOperation={onApprovedOperation} />;
  }
  if (renderer === "SCIENCE_PROCESS_SEQUENCE") {
    return <ProcessSequenceWorkspace sceneId={scene.scene_id} sceneVersion={scene.scene_version} state={readProcessSequenceState(state)} locale={scene.locale} direction={scene.direction} onOperation={onApprovedOperation} />;
  }
  if (renderer === "ARABIC_SENTENCE_ORDERING") {
    return <ArabicSentenceOrderingWorkspace sceneId={scene.scene_id} sceneVersion={scene.scene_version} state={readArabicSentenceOrderingState(state)} onOperation={onApprovedOperation} />;
  }
  return <SentenceOrderingWorkspace sceneId={scene.scene_id} sceneVersion={scene.scene_version} state={readSentenceOrderingState(state)} locale={scene.locale} direction={scene.direction} onOperation={onApprovedOperation} />;
}
