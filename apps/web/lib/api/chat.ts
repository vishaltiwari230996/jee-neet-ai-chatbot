/**
 * Streaming chat client.
 *
 * Reads the SSE stream from `POST /api/v1/chat/stream` and yields
 * `ChatStreamEvent`s. We do *not* use `EventSource` because it only
 * supports GET; streaming a POST body requires the Fetch streaming API.
 *
 * Cancellation is the caller's responsibility — pass an `AbortSignal`
 * and the connection (and its OpenRouter upstream) closes cleanly.
 */

import type {
  ApiErrorBody,
  ChatStreamEvent,
  ChatStreamRequest,
} from "./types";
import { ApiError } from "./client";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export async function* streamChat(
  body: ChatStreamRequest,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent, void, void> {
  const res = await fetch(`${BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });

  if (!res.ok || !res.body) {
    let parsed: ApiErrorBody;
    try {
      parsed = (await res.json()) as ApiErrorBody;
    } catch {
      parsed = {
        code: "network_error",
        message: `Chat request failed (${res.status})`,
      };
    }
    throw new ApiError(res.status, parsed);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      let separatorIndex = buffer.indexOf("\n\n");
      while (separatorIndex !== -1) {
        const frame = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);

        const event = parseFrame(frame);
        if (event) yield event;

        separatorIndex = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): ChatStreamEvent | null {
  let eventName = "message";
  let dataLine = "";

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLine = line.slice("data:".length).trim();
    }
  }

  if (!dataLine) return null;

  let payload: unknown;
  try {
    payload = JSON.parse(dataLine);
  } catch {
    return null;
  }

  if (eventName === "delta" && typeof payload === "object" && payload !== null) {
    const { text } = payload as { text?: unknown };
    if (typeof text === "string") return { kind: "delta", text };
  }
  if (eventName === "done" && typeof payload === "object" && payload !== null) {
    const obj = payload as {
      model?: string | null;
      usage?: { input_tokens: number; output_tokens: number } | null;
      cost_usd?: number | null;
    };
    return {
      kind: "done",
      model: obj.model ?? null,
      usage: obj.usage ?? null,
      cost_usd: obj.cost_usd ?? null,
    };
  }
  if (eventName === "error" && typeof payload === "object" && payload !== null) {
    const { message } = payload as { message?: unknown };
    if (typeof message === "string") return { kind: "error", message };
  }
  return null;
}
