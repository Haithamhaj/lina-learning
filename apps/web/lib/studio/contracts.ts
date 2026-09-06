export const STUDIO_PROTOCOL_VERSION = "studio-protocol-v1" as const;

export type StudioActiveSceneContract = {
  scene_id: string;
  scene_version: number;
  subject_key: string;
  subject_profile_version: string;
  activity_key: string;
  activity_contract_version: string;
  renderer_key: string;
  renderer_version: string;
  payload_schema_version: string;
  locale: string;
  direction: "ltr" | "rtl" | "auto";
};

export type StudioSnapshotFrame = {
  protocol_version: typeof STUDIO_PROTOCOL_VERSION;
  type: "STUDIO_SNAPSHOT";
  latest_event_sequence: number;
  snapshot_schema_version: string;
  current_scene_id: string | null;
  current_scene_version: number | null;
  active_subject_key: string | null;
  active_activity_key: string | null;
  active_step_key: string | null;
  state_payload: Record<string, unknown>;
  active_scene_contract: StudioActiveSceneContract | null;
  active_scene_seed: Record<string, unknown> | null;
};

export type StudioEventCommittedFrame = {
  protocol_version: typeof STUDIO_PROTOCOL_VERSION;
  type: "STUDIO_EVENT_COMMITTED";
  sequence: number;
  event: {
    id: string;
    sequence: number;
    actor: string;
    event_kind: string;
    action_key: string | null;
    event_schema_version: string;
    payload_schema_version: string;
    scene_id: string | null;
    base_scene_version: number | null;
    resulting_scene_version: number | null;
    payload: Record<string, unknown>;
    result_status: "ACCEPTED";
  };
};

export type StudioErrorFrame = {
  protocol_version: typeof STUDIO_PROTOCOL_VERSION;
  type: "STUDIO_ERROR";
  code: "STUDIO_FEED_UNAVAILABLE" | "STUDIO_PROTOCOL_ERROR";
};

export type StudioFrame = StudioSnapshotFrame | StudioEventCommittedFrame | StudioErrorFrame;

export type StudioOperation = {
  scene_id: string;
  base_scene_version: number;
  action_key: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
};

export class StudioProtocolParseError extends Error {}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function nullableString(value: unknown): value is string | null {
  return typeof value === "string" || value === null;
}

function nullableNonNegativeInteger(value: unknown): value is number | null {
  return value === null || nonNegativeInteger(value);
}

function activeSceneContract(value: unknown): value is StudioActiveSceneContract {
  if (!isRecord(value)) return false;
  return (
    typeof value.scene_id === "string"
    && nonNegativeInteger(value.scene_version)
    && typeof value.subject_key === "string"
    && typeof value.subject_profile_version === "string"
    && typeof value.activity_key === "string"
    && typeof value.activity_contract_version === "string"
    && typeof value.renderer_key === "string"
    && typeof value.renderer_version === "string"
    && typeof value.payload_schema_version === "string"
    && typeof value.locale === "string"
    && (value.direction === "ltr" || value.direction === "rtl" || value.direction === "auto")
  );
}

export function parseStudioFrame(value: unknown): StudioFrame {
  if (!isRecord(value) || value.protocol_version !== STUDIO_PROTOCOL_VERSION || typeof value.type !== "string") {
    throw new StudioProtocolParseError("Invalid Studio protocol frame.");
  }
  if (value.type === "STUDIO_SNAPSHOT") {
    if (
      !nonNegativeInteger(value.latest_event_sequence)
      || typeof value.snapshot_schema_version !== "string"
      || !isRecord(value.state_payload)
      || !nullableString(value.current_scene_id)
      || !nullableNonNegativeInteger(value.current_scene_version)
      || !nullableString(value.active_subject_key)
      || !nullableString(value.active_activity_key)
      || !nullableString(value.active_step_key)
      || (value.active_scene_contract !== null && !activeSceneContract(value.active_scene_contract))
      || (value.active_scene_seed !== null && !isRecord(value.active_scene_seed))
    ) {
      throw new StudioProtocolParseError("Invalid Studio snapshot frame.");
    }
    if (value.active_scene_contract === null) {
      if (value.active_scene_seed !== null) throw new StudioProtocolParseError("Studio snapshot exposes a Scene seed without an active Scene.");
    } else if (
      value.current_scene_id !== value.active_scene_contract.scene_id
      || value.current_scene_version !== value.active_scene_contract.scene_version
      || value.active_subject_key !== value.active_scene_contract.subject_key
      || value.active_activity_key !== value.active_scene_contract.activity_key
    ) {
      throw new StudioProtocolParseError("Studio snapshot Scene identity does not match its active contract.");
    } else if (!isRecord(value.active_scene_seed)) {
      throw new StudioProtocolParseError("Studio snapshot active Scene is missing its safe seed.");
    }
    return value as StudioSnapshotFrame;
  }
  if (value.type === "STUDIO_EVENT_COMMITTED") {
    if (!nonNegativeInteger(value.sequence) || !isRecord(value.event) || value.event.sequence !== value.sequence || typeof value.event.event_kind !== "string") {
      throw new StudioProtocolParseError("Invalid Studio event frame.");
    }
    return value as StudioEventCommittedFrame;
  }
  if (value.type === "STUDIO_ERROR") {
    if (value.code !== "STUDIO_FEED_UNAVAILABLE" && value.code !== "STUDIO_PROTOCOL_ERROR") {
      throw new StudioProtocolParseError("Invalid Studio error frame.");
    }
    return value as StudioErrorFrame;
  }
  throw new StudioProtocolParseError("Unsupported Studio protocol frame type.");
}
