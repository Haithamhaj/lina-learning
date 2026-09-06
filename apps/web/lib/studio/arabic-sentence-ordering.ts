import type { StudioOperation } from "./contracts";

export const ARABIC_SENTENCE_ORDERING_ACTIVITY_KEY = "arabic_sentence_ordering_workspace" as const;
export const REORDER_TOKEN_ACTION_KEY = "REORDER_TOKEN" as const;
export const SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION" as const;
export type ArabicSentenceOrderingTokenId = "tok-6d3a" | "tok-f18c" | "tok-2b7e";
export type ArabicSentenceOrderingToken = { id: ArabicSentenceOrderingTokenId; text: string };
export type ArabicSentenceOrderingState = {
  fixture_key: "arabic_sentence_ordering_fixture_orchid";
  fixture_version: "arabic-sentence-ordering-fixture-orchid-v1";
  token_schema_version: "arabic-sentence-ordering-token-v1";
  tokens: ArabicSentenceOrderingToken[];
  token_ids: ArabicSentenceOrderingTokenId[];
};

const catalog: ArabicSentenceOrderingToken[] = [
  { id: "tok-2b7e", text: "الدرسَ" }, { id: "tok-6d3a", text: "تكتبُ" }, { id: "tok-f18c", text: "الطالبةُ" },
];
const ids = new Set<ArabicSentenceOrderingTokenId>(catalog.map((token) => token.id));
type Base = Omit<StudioOperation, "action_key" | "payload">;
export type ArabicSentenceOrderingOperation = (Base & { action_key: typeof REORDER_TOKEN_ACTION_KEY; payload: { token_id: ArabicSentenceOrderingTokenId; from_index: number; to_index: number } }) | (Base & { action_key: typeof SUBMIT_CONFIGURATION_ACTION_KEY; payload: { token_ids: ArabicSentenceOrderingTokenId[] } });

export function readArabicSentenceOrderingState(value: unknown): ArabicSentenceOrderingState | null {
  if (!record(value) || !allowedStateShape(value) || value.fixture_key !== "arabic_sentence_ordering_fixture_orchid" || value.fixture_version !== "arabic-sentence-ordering-fixture-orchid-v1" || value.token_schema_version !== "arabic-sentence-ordering-token-v1" || !Array.isArray(value.tokens) || !Array.isArray(value.token_ids)) return null;
  const tokens = value.tokens.map((token) => record(token) && Object.keys(token).length === 2 && typeof token.id === "string" && ids.has(token.id as ArabicSentenceOrderingTokenId) && typeof token.text === "string" && token.text ? { id: token.id as ArabicSentenceOrderingTokenId, text: token.text } : null);
  if (tokens.some((token) => token === null) || !sameCatalog(tokens as ArabicSentenceOrderingToken[]) || !validIds(value.token_ids) || !validLastSubmission(value.last_submission)) return null;
  return { fixture_key: "arabic_sentence_ordering_fixture_orchid", fixture_version: "arabic-sentence-ordering-fixture-orchid-v1", token_schema_version: "arabic-sentence-ordering-token-v1", tokens: tokens as ArabicSentenceOrderingToken[], token_ids: [...value.token_ids] };
}

export function makeArabicReorderOperation(state: ArabicSentenceOrderingState, sceneId: string, sceneVersion: number, tokenId: string, fromIndex: number, toIndex: number, idempotencyKey: string): ArabicSentenceOrderingOperation | null {
  if (!sceneId || !Number.isInteger(sceneVersion) || sceneVersion < 0 || !idempotencyKey || !ids.has(tokenId as ArabicSentenceOrderingTokenId) || !Number.isInteger(fromIndex) || !Number.isInteger(toIndex) || fromIndex < 0 || toIndex < 0 || fromIndex >= state.token_ids.length || toIndex >= state.token_ids.length || fromIndex === toIndex || state.token_ids[fromIndex] !== tokenId) return null;
  return { scene_id: sceneId, base_scene_version: sceneVersion, action_key: REORDER_TOKEN_ACTION_KEY, payload: { token_id: tokenId as ArabicSentenceOrderingTokenId, from_index: fromIndex, to_index: toIndex }, idempotency_key: idempotencyKey };
}

export function makeArabicSubmitOperation(state: ArabicSentenceOrderingState, sceneId: string, sceneVersion: number, idempotencyKey: string): ArabicSentenceOrderingOperation | null {
  if (!sceneId || !Number.isInteger(sceneVersion) || sceneVersion < 0 || !idempotencyKey || !validIds(state.token_ids)) return null;
  return { scene_id: sceneId, base_scene_version: sceneVersion, action_key: SUBMIT_CONFIGURATION_ACTION_KEY, payload: { token_ids: [...state.token_ids] }, idempotency_key: idempotencyKey };
}

function validIds(value: unknown[]): value is ArabicSentenceOrderingTokenId[] { return value.length === catalog.length && value.every((id): id is ArabicSentenceOrderingTokenId => typeof id === "string" && ids.has(id as ArabicSentenceOrderingTokenId)) && new Set(value).size === catalog.length; }
function sameCatalog(value: ArabicSentenceOrderingToken[]): boolean { return value.length === catalog.length && new Set(value.map(token => token.id)).size === catalog.length && value.every((token) => catalog.some((expected) => expected.id === token.id && expected.text === token.text)); }
function validLastSubmission(value: unknown): boolean { return value === undefined || (record(value) && Object.keys(value).length === 1 && Array.isArray(value.token_ids) && validIds(value.token_ids)); }
function allowedStateShape(value: Record<string, unknown>): boolean { return Object.keys(value).every((key) => ["fixture_key", "fixture_version", "token_schema_version", "tokens", "token_ids", "last_submission"].includes(key)); }
function record(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
