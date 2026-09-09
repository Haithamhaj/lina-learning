export type WorkspacePresentation = { hiddenSceneId: string | null; visible: boolean };

/** Client-only visibility choice; the server Snapshot remains the Scene authority. */
export function nextWorkspacePresentation(activeSceneId: string | null, hiddenSceneId: string | null): WorkspacePresentation {
  if (activeSceneId === null) return { hiddenSceneId: null, visible: false };
  if (activeSceneId === hiddenSceneId) return { hiddenSceneId, visible: false };
  return { hiddenSceneId: null, visible: true };
}
