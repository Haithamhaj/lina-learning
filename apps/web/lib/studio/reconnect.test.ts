import assert from "node:assert/strict";
import test from "node:test";

import { createStudioReconnectLoop } from "./reconnect.ts";

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((yes) => { resolve = yes; });
  return { promise, resolve };
}

function flushMicrotasks() {
  return new Promise<void>((resolve) => setImmediate(resolve));
}

test("Studio reconnect retries recovery automatically and never opens duplicate feeds", async () => {
  const timers: Array<() => void> = [];
  const feeds = [deferred(), deferred()];
  let connectCount = 0;
  let recoverCount = 0;
  const states: string[] = [];
  const errors: string[] = [];
  const loop = createStudioReconnectLoop({
    connect: () => {
      const feed = feeds[connectCount];
      connectCount += 1;
      if (!feed) throw new Error("duplicate connection");
      return { close: () => {}, done: feed.promise };
    },
    recover: async () => {
      recoverCount += 1;
      if (recoverCount === 1) throw new Error("temporary snapshot failure");
    },
    onStateChange: (state) => states.push(state),
    onRecoverError: (error) => errors.push(String(error)),
    setTimeout: (callback) => { timers.push(callback); return timers.length; },
    clearTimeout: () => {},
  });

  loop.start();
  loop.start();
  assert.equal(connectCount, 1);
  feeds[0]?.resolve();
  await flushMicrotasks();
  assert.equal(timers.length, 1);

  timers.shift()?.();
  await flushMicrotasks();
  assert.equal(recoverCount, 1);
  assert.equal(connectCount, 1);
  assert.equal(timers.length, 1, "failed recovery schedules the next policy attempt");

  timers.shift()?.();
  await flushMicrotasks();
  assert.equal(recoverCount, 2);
  assert.equal(connectCount, 2);
  assert.deepEqual(states, ["connected", "reconnecting", "reconnecting", "connected"]);
  assert.equal(errors.length, 1);
});

test("Studio reconnect cleanup cancels a pending retry and closes the active feed", async () => {
  const feed = deferred();
  const timers = new Map<number, () => void>();
  let nextTimer = 0;
  let closeCount = 0;
  let connectCount = 0;
  const loop = createStudioReconnectLoop({
    connect: () => {
      connectCount += 1;
      return { close: () => { closeCount += 1; }, done: feed.promise };
    },
    recover: async () => {},
    onStateChange: () => {},
    onRecoverError: () => {},
    setTimeout: (callback) => { nextTimer += 1; timers.set(nextTimer, callback); return nextTimer; },
    clearTimeout: (id) => { timers.delete(id); },
  });

  loop.start();
  feed.resolve();
  await flushMicrotasks();
  assert.equal(timers.size, 1);
  loop.dispose();

  assert.equal(timers.size, 0);
  assert.equal(closeCount, 1);
  assert.equal(connectCount, 1);
});
