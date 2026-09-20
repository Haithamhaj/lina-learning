export type ForegroundGate = { current: boolean };

/** Acquire synchronously so two browser events in one render cannot both write. */
export function acquireForegroundGate(gate: ForegroundGate): boolean {
  if (gate.current) return false;
  gate.current = true;
  return true;
}

export function releaseForegroundGate(gate: ForegroundGate): void {
  gate.current = false;
}
