export type StudioReconnectState = "connected" | "reconnecting";

type StudioConnection = { close: () => void; done: Promise<void> };

type ReconnectLoopOptions = {
  connect: () => StudioConnection;
  recover: () => Promise<void>;
  onStateChange: (state: StudioReconnectState) => void;
  onRecoverError: (error: unknown) => void;
  onRecovered?: () => void;
  setTimeout?: (callback: () => void, milliseconds: number) => number;
  clearTimeout?: (id: number) => void;
};

/** One policy-owned feed/recovery loop with deterministic cleanup semantics. */
export function createStudioReconnectLoop(options: ReconnectLoopOptions) {
  const schedule = options.setTimeout ?? window.setTimeout;
  const unschedule = options.clearTimeout ?? window.clearTimeout;
  let disposed = false;
  let feed: StudioConnection | null = null;
  let reconnectTimer: number | null = null;
  let recoveryActive = false;
  let retryCount = 0;

  const delay = () => Math.min(4_000, 600 * Math.max(1, retryCount));

  const queueRecovery = () => {
    if (disposed || reconnectTimer !== null || recoveryActive) return;
    reconnectTimer = schedule(() => {
      reconnectTimer = null;
      if (disposed || recoveryActive) return;
      recoveryActive = true;
      void options.recover().then(() => {
        if (disposed) return;
        options.onRecovered?.();
        openFeed();
      }).catch((error: unknown) => {
        if (disposed) return;
        retryCount += 1;
        options.onRecoverError(error);
        options.onStateChange("reconnecting");
        queueRecovery();
      }).finally(() => {
        recoveryActive = false;
        if (!disposed && feed === null && reconnectTimer === null) queueRecovery();
      });
    }, delay());
  };

  const openFeed = () => {
    if (disposed || feed !== null) return;
    options.onStateChange("connected");
    const opened = options.connect();
    feed = opened;
    const settled = () => {
      if (feed === opened) {
        opened.close();
        feed = null;
      }
      if (disposed) return;
      retryCount += 1;
      options.onStateChange("reconnecting");
      queueRecovery();
    };
    void opened.done.then(settled, settled);
  };

  return {
    start: openFeed,
    dispose() {
      disposed = true;
      if (reconnectTimer !== null) unschedule(reconnectTimer);
      reconnectTimer = null;
      feed?.close();
      feed = null;
    },
  };
}
