import { ApiError } from "@/shared/api/errors";
import { apiRequest, buildApiUrl } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { readSseStream } from "@/shared/api/stream";
import { createId } from "@/shared/lib/id";

import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  ChatStreamMeta,
  ChatToolCall,
} from "@/features/chat/types";

type BackendChatMessage = {
  role: ChatMessage["role"];
  content: string;
  name: string | null;
  metadata: Record<string, unknown>;
};

type BackendChatToolCall = {
  tool_name: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

type BackendChatRequest = {
  messages: BackendChatMessage[];
  conversation_id?: string;
  user_id?: string;
  metadata: Record<string, unknown>;
};

type BackendChatResponse = {
  conversation_id: string | null;
  message: BackendChatMessage;
  messages: BackendChatMessage[];
  metadata: Record<string, unknown>;
  tool_calls: BackendChatToolCall[];
};

type BackendChatStreamEvent = {
  type: "start" | "message" | "error" | "done";
  content?: string | null;
  data: Record<string, unknown>;
};

function mapChatMessage(message: BackendChatMessage): ChatMessage {
  return {
    role: message.role,
    content: message.content,
    name: message.name,
    metadata: message.metadata,
  };
}

function mapToolCall(toolCall: BackendChatToolCall): ChatToolCall {
  return {
    toolName: toolCall.tool_name,
    status: toolCall.status,
    input: toolCall.input,
    output: toolCall.output,
    metadata: toolCall.metadata,
  };
}

function buildChatRequest(payload: ChatRequest): BackendChatRequest {
  return {
    messages: payload.messages.map((message) => ({
      role: message.role,
      content: message.content,
      name: message.name ?? null,
      metadata: message.metadata ?? {},
    })),
    conversation_id: payload.conversationId,
    user_id: payload.userId,
    metadata: payload.metadata ?? {},
  };
}

function mapChatResponse(data: BackendChatResponse): ChatResponse {
  return {
    conversationId: data.conversation_id,
    message: mapChatMessage(data.message),
    messages: data.messages.map(mapChatMessage),
    metadata: data.metadata,
    toolCalls: data.tool_calls.map(mapToolCall),
  };
}

function readStreamMeta(data: Record<string, unknown>): ChatStreamMeta {
  const conversationId = data.conversation_id;
  const runId = data.run_id;

  return {
    conversationId:
      typeof conversationId === "string" && conversationId.length > 0
        ? conversationId
        : null,
    runId: typeof runId === "string" && runId.length > 0 ? runId : null,
  };
}

function buildStreamHeaders() {
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  headers.set("X-Request-Id", createId("req"));
  return headers;
}

function parseStreamEvent(raw: string): BackendChatStreamEvent {
  return JSON.parse(raw) as BackendChatStreamEvent;
}

type StreamChatCallbacks = {
  onStart?: (meta: ChatStreamMeta) => void;
  onMessage?: (content: string) => void;
  onDone?: (response: ChatResponse) => void;
  onError?: (error: ApiError) => void;
};

export function sendChat(payload: ChatRequest) {
  return apiRequest<BackendChatResponse>(API_ENDPOINTS.chat, {
    method: "POST",
    body: JSON.stringify(buildChatRequest(payload)),
  }).then<ChatResponse>(mapChatResponse);
}

export async function streamChat(
  payload: ChatRequest,
  callbacks: StreamChatCallbacks,
) {
  const response = await fetch(
    buildApiUrl(API_ENDPOINTS.chatStream),
    {
      method: "POST",
      headers: buildStreamHeaders(),
      body: JSON.stringify(buildChatRequest(payload)),
    },
  );

  if (!response.ok) {
    throw new ApiError(`Request failed: ${response.status}`, response.status, {
      traceId: response.headers.get("X-Trace-Id") ?? undefined,
      requestId: response.headers.get("X-Request-Id") ?? undefined,
    });
  }

  await readSseStream(response, (eventName, rawData) => {
    const event = parseStreamEvent(rawData);

    if (eventName === "start") {
      callbacks.onStart?.(readStreamMeta(event.data));
      return;
    }

    if (eventName === "message") {
      callbacks.onMessage?.(event.content ?? "");
      return;
    }

    if (eventName === "done") {
      callbacks.onDone?.(
        mapChatResponse(event.data as unknown as BackendChatResponse),
      );
      return;
    }

    if (eventName === "error") {
      const code = event.data.code;
      callbacks.onError?.(
        new ApiError(event.content ?? "流式聊天失败", response.status, {
          code: typeof code === "string" ? code : undefined,
          traceId: response.headers.get("X-Trace-Id") ?? undefined,
          requestId: response.headers.get("X-Request-Id") ?? undefined,
          data: event.data,
        }),
      );
    }
  });
}
