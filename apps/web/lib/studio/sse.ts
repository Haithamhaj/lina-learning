import { parseStudioFrame, StudioFrame, StudioProtocolParseError } from "./contracts";

export type ParsedStudioSseFrame = { id: number | null; frame: StudioFrame };

/** Incremental SSE parser kept separate from browser authentication and UI state. */
export class StudioSseParser {
  private buffer = "";
  private eventId: number | null = null;
  private eventType: string | null = null;
  private data: string[] = [];

  push(chunk: string): ParsedStudioSseFrame[] {
    this.buffer += chunk.replace(/\r\n/g, "\n");
    const frames: ParsedStudioSseFrame[] = [];
    let boundary: number;
    while ((boundary = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, boundary);
      this.buffer = this.buffer.slice(boundary + 1);
      if (!line) {
        const next = this.dispatch();
        if (next) frames.push(next);
        continue;
      }
      if (line.startsWith(":")) continue;
      const separator = line.indexOf(":");
      const field = separator < 0 ? line : line.slice(0, separator);
      const raw = separator < 0 ? "" : line.slice(separator + 1).replace(/^ /, "");
      if (field === "id") {
        if (!/^\d+$/.test(raw)) throw new StudioProtocolParseError("Studio SSE id must be non-negative.");
        this.eventId = Number(raw);
      } else if (field === "event") {
        this.eventType = raw;
      } else if (field === "data") {
        this.data.push(raw);
      }
    }
    return frames;
  }

  private dispatch(): ParsedStudioSseFrame | null {
    if (this.data.length === 0) {
      this.eventType = null;
      return null;
    }
    let decoded: unknown;
    try {
      decoded = JSON.parse(this.data.join("\n"));
    } catch {
      throw new StudioProtocolParseError("Studio SSE payload is not JSON.");
    }
    const frame = parseStudioFrame(decoded);
    if (this.eventType !== frame.type) throw new StudioProtocolParseError("Studio SSE event type does not match payload.");
    const result = { id: this.eventId, frame };
    this.eventId = null;
    this.eventType = null;
    this.data = [];
    return result;
  }
}
