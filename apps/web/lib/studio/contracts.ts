export const STUDIO_PROTOCOL_VERSION = "studio-protocol-v1" as const;

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

export function parseStudioFrame(value: unknown): StudioFrame {
  if (!isRecord(value) || value.protocol_version !== STUDIO_PROTOCOL_VERSION || typeof value.type !== "string") {
    throw new StudioProtocolParseError("Invalid Studio protocol frame.");
  }
  if (value.type === "STUDIO_SNAPSHOT") {
    if (!nonNegativeInteger(value.latest_event_sequence) || typeof value.snapshot_schema_version !== "string" || !isRecord(value.state_payload)) {
      throw new StudioProtocolParseError("Invalid Studio snapshot frame.");
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
