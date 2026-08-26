export const INCOMPLETE_TUTOR_RESPONSE_ERROR = "The Tutor response did not finish. Please try again.";

export type TutorStreamTermination = "eof" | "error";

type TutorMessage = { id: string };

type TutorStreamFinalization<TMessage extends TutorMessage> = {
  messages: TMessage[];
  state: "ready" | "error";
  error: string | null;
  lifecycleEvent: "stream_incomplete" | "request_error" | null;
};

export function finalizeTutorStream<TMessage extends TutorMessage>({
  messages,
  provisionalTutorMessageId,
  terminalTurnReceived,
  termination,
}: {
  messages: TMessage[];
  provisionalTutorMessageId: string;
  terminalTurnReceived: boolean;
  termination: TutorStreamTermination;
}): TutorStreamFinalization<TMessage> {
  if (terminalTurnReceived) {
    return { messages, state: "ready", error: null, lifecycleEvent: null };
  }

  return {
    messages: messages.filter((message) => message.id !== provisionalTutorMessageId),
    state: "error",
    error: INCOMPLETE_TUTOR_RESPONSE_ERROR,
    lifecycleEvent: termination === "eof" ? "stream_incomplete" : "request_error",
  };
}
