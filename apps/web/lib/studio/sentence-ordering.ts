import type { StudioOperation } from "./contracts";

export const SENTENCE_ORDERING_ACTIVITY_KEY = "sentence_ordering_workspace" as const;
export const REORDER_TOKEN_ACTION_KEY = "REORDER_TOKEN" as const;
export const SUBMIT_CONFIGURATION_ACTION_KEY = "SUBMIT_CONFIGURATION" as const;

export type SentenceOrderingTokenId =
  | "tok-c820"
  | "tok-43bd"
  | "tok-7f2c"
  | "tok-a91e";

export type SentenceOrderingToken = {
  id: SentenceOrderingTokenId;
  text: string;
};

export type SentenceOrderingState = {
  fixture_key: "english_sentence_ordering_fixture_slate";
  fixture_version: "english-sentence-ordering-fixture-slate-v1";
  token_schema_version: "sentence-ordering-token-v1";
  tokens: SentenceOrderingToken[];
  token_ids: SentenceOrderingTokenId[];
};

type ReorderPayload = {
  token_id: SentenceOrderingTokenId;
  from_index: number;
  to_index: number;
};

type SubmitPayload = {
  token_ids: SentenceOrderingTokenId[];
};

type SentenceOrderingOperationBase = Omit<StudioOperation, "action_key" | "payload">;

export type ReorderTokenOperation = SentenceOrderingOperationBase & {
  action_key: typeof REORDER_TOKEN_ACTION_KEY;
  payload: ReorderPayload;
};

export type SubmitConfigurationOperation = SentenceOrderingOperationBase & {
  action_key: typeof SUBMIT_CONFIGURATION_ACTION_KEY;
  payload: SubmitPayload;
};

export type SentenceOrderingOperation = ReorderTokenOperation | SubmitConfigurationOperation;

// Browser-safe scene content for the isolated review mount. The accepted order
// remains server-owned and is intentionally absent from this renderer model.
const reviewTokens: SentenceOrderingToken[] = [
  { id: "tok-7f2c", text: "over" },
  { id: "tok-a91e", text: "clouds" },
  { id: "tok-43bd", text: "fly" },
  { id: "tok-c820", text: "Birds" },
];

const tokenIds = new Set<SentenceOrderingTokenId>(reviewTokens.map((token) => token.id));

export function sentenceOrderingReviewState(): SentenceOrderingState {
  return {
    fixture_key: "english_sentence_ordering_fixture_slate",
    fixture_version: "english-sentence-ordering-fixture-slate-v1",
    token_schema_version: "sentence-ordering-token-v1",
    tokens: reviewTokens.map((token) => ({ ...token })),
    token_ids: ["tok-a91e", "tok-c820", "tok-7f2c", "tok-43bd"],
  };
}

export function readSentenceOrderingState(value: unknown): SentenceOrderingState | null {
  if (
    !isRecord(value)
    || value.fixture_key !== "english_sentence_ordering_fixture_slate"
    || value.fixture_version !== "english-sentence-ordering-fixture-slate-v1"
    || value.token_schema_version !== "sentence-ordering-token-v1"
    || !Array.isArray(value.tokens)
    || !Array.isArray(value.token_ids)
  ) return null;
  const tokens = value.tokens.map(readToken);
  if (tokens.some((token): token is null => token === null) || !sameTokenCatalog(tokens as SentenceOrderingToken[])) return null;
  if (!validTokenIds(value.token_ids)) return null;
  return {
    fixture_key: "english_sentence_ordering_fixture_slate",
    fixture_version: "english-sentence-ordering-fixture-slate-v1",
    token_schema_version: "sentence-ordering-token-v1",
    tokens: tokens as SentenceOrderingToken[],
    token_ids: [...value.token_ids],
  };
}

export function makeReorderOperation(
  state: SentenceOrderingState,
  sceneId: string,
  sceneVersion: number,
  tokenId: string,
  fromIndex: number,
  toIndex: number,
  idempotencyKey: string,
): ReorderTokenOperation | null {
  if (
    !sceneId
    || !Number.isInteger(sceneVersion)
    || sceneVersion < 0
    || !idempotencyKey
    || !tokenIds.has(tokenId as SentenceOrderingTokenId)
    || !Number.isInteger(fromIndex)
    || !Number.isInteger(toIndex)
    || fromIndex < 0
    || toIndex < 0
    || fromIndex >= state.token_ids.length
    || toIndex >= state.token_ids.length
    || fromIndex === toIndex
    || state.token_ids[fromIndex] !== tokenId
  ) return null;
  return {
    scene_id: sceneId,
    base_scene_version: sceneVersion,
    action_key: REORDER_TOKEN_ACTION_KEY,
    payload: { token_id: tokenId as SentenceOrderingTokenId, from_index: fromIndex, to_index: toIndex },
    idempotency_key: idempotencyKey,
  };
}

export function makeSubmitOperation(
  state: SentenceOrderingState,
  sceneId: string,
  sceneVersion: number,
  idempotencyKey: string,
): SubmitConfigurationOperation | null {
  if (!sceneId || !Number.isInteger(sceneVersion) || sceneVersion < 0 || !idempotencyKey || !validTokenIds(state.token_ids)) return null;
  return {
    scene_id: sceneId,
    base_scene_version: sceneVersion,
    action_key: SUBMIT_CONFIGURATION_ACTION_KEY,
    payload: { token_ids: [...state.token_ids] },
    idempotency_key: idempotencyKey,
  };
}

/** Review-mount-only echo. Production renderers must await Studio authority. */
export function applyMockSentenceOrderingOperation(
  state: SentenceOrderingState,
  operation: SentenceOrderingOperation,
): SentenceOrderingState {
  if (operation.action_key !== REORDER_TOKEN_ACTION_KEY) return state;
  const { token_id: tokenId, from_index: fromIndex, to_index: toIndex } = operation.payload;
  if (
    state.token_ids[fromIndex] !== tokenId
    || fromIndex === toIndex
    || fromIndex < 0
    || toIndex < 0
    || fromIndex >= state.token_ids.length
    || toIndex >= state.token_ids.length
  ) return state;
  const tokenIdsAfter = [...state.token_ids];
  tokenIdsAfter.splice(fromIndex, 1);
  tokenIdsAfter.splice(toIndex, 0, tokenId);
  return { ...state, token_ids: tokenIdsAfter };
}

function validTokenIds(value: unknown[]): value is SentenceOrderingTokenId[] {
  return value.length === reviewTokens.length && value.every((id): id is SentenceOrderingTokenId => typeof id === "string" && tokenIds.has(id as SentenceOrderingTokenId)) && new Set(value).size === reviewTokens.length;
}

function readToken(value: unknown): SentenceOrderingToken | null {
  if (!isRecord(value) || !tokenIds.has(value.id as SentenceOrderingTokenId) || typeof value.text !== "string" || !value.text) return null;
  return { id: value.id as SentenceOrderingTokenId, text: value.text };
}

function sameTokenCatalog(tokens: SentenceOrderingToken[]): boolean {
  return tokens.length === reviewTokens.length && new Set(tokens.map((token) => token.id)).size === reviewTokens.length;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
