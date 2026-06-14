import { ApiError } from "@/shared/api/errors";
import { apiRequest, buildApiUrl } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { readSseStream } from "@/shared/api/stream";
import { createId } from "@/shared/lib/id";
import { mapPendingHumanInput } from "@/features/chat/pendingHumanInput";

import type {
  ChatInterruptPayload,
  ChatMessage,
  ChatRequest,
  ChatResumeRequest,
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
  repository_context?: Record<string, unknown>;
  changed_files?: string[];
  task_type?: string | null;
};

type BackendChatResponse = {
  conversation_id: string | null;
  agent_id?: string | null;
  message: BackendChatMessage;
  messages: BackendChatMessage[];
  metadata: Record<string, unknown>;
  tool_calls: BackendChatToolCall[];
  pending_human_input?: unknown;
};

type BackendChatStreamEvent = {
  type: "start" | "message" | "interrupt" | "error" | "done";
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
    repository_context: payload.repositoryContext,
    changed_files: payload.changedFiles,
    task_type: payload.taskType,
  };
}

function mapChatResponse(data: BackendChatResponse): ChatResponse {
  const metadataAgentId = data.metadata.agent_id;
  return {
    conversationId: data.conversation_id,
    agentId:
      typeof data.agent_id === "string"
        ? data.agent_id
        : typeof metadataAgentId === "string"
          ? metadataAgentId
          : null,
    message: mapChatMessage(data.message),
    messages: data.messages.map(mapChatMessage),
    metadata: data.metadata,
    toolCalls: data.tool_calls.map(mapToolCall),
    pendingHumanInput: mapPendingHumanInput(data.pending_human_input),
  };
}

function readStreamMeta(data: Record<string, unknown>): ChatStreamMeta {
  const conversationId = data.conversation_id;
  const runId = data.run_id;
  const agentId = data.agent_id;

  return {
    conversationId:
      typeof conversationId === "string" && conversationId.length > 0
        ? conversationId
        : null,
    runId: typeof runId === "string" && runId.length > 0 ? runId : null,
    agentId: typeof agentId === "string" && agentId.length > 0 ? agentId : null,
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
  onInterrupt?: (payload: ChatInterruptPayload) => void;
  onDone?: (response: ChatResponse) => void;
  onError?: (error: ApiError) => void;
};

export type AgentChatInput = {
  agentId: string;
  payload: ChatRequest;
};

export function sendChat(payload: ChatRequest) {
  return apiRequest<BackendChatResponse>(API_ENDPOINTS.chat, {
    method: "POST",
    body: JSON.stringify(buildChatRequest(payload)),
  }).then<ChatResponse>(mapChatResponse);
}

export function resumeChat(payload: ChatResumeRequest) {
  return apiRequest<BackendChatResponse>(API_ENDPOINTS.chatResume, {
    method: "POST",
    body: JSON.stringify({
      run_id: payload.runId,
      input: payload.input,
    }),
  }).then<ChatResponse>(mapChatResponse);
}

export function sendAgentChat({ agentId, payload }: AgentChatInput) {
  return apiRequest<BackendChatResponse>(API_ENDPOINTS.agentChat(agentId), {
    method: "POST",
    body: JSON.stringify(buildChatRequest(payload)),
  }).then<ChatResponse>(mapChatResponse);
}

export async function streamChat(
  payload: ChatRequest,
  callbacks: StreamChatCallbacks,
) {
  const response = await fetch(buildApiUrl(API_ENDPOINTS.chatStream), {
    method: "POST",
    headers: buildStreamHeaders(),
    body: JSON.stringify(buildChatRequest(payload)),
  });

  return consumeStreamResponse(response, callbacks);
}

export async function streamResumeChat(
  payload: ChatResumeRequest,
  callbacks: StreamChatCallbacks,
) {
  const response = await fetch(buildApiUrl(API_ENDPOINTS.chatResumeStream), {
    method: "POST",
    headers: buildStreamHeaders(),
    body: JSON.stringify({
      run_id: payload.runId,
      input: payload.input,
    }),
  });

  return consumeStreamResponse(response, callbacks);
}

export async function streamAgentChat(
  input: AgentChatInput,
  callbacks: StreamChatCallbacks,
) {
  const response = await fetch(buildApiUrl(API_ENDPOINTS.agentChatStream(input.agentId)), {
    method: "POST",
    headers: buildStreamHeaders(),
      body: JSON.stringify(buildChatRequest(input.payload)),
  });

  return consumeStreamResponse(response, callbacks);
}

async function consumeStreamResponse(
  response: Response,
  callbacks: StreamChatCallbacks,
) {
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

    if (eventName === "interrupt") {
      const pendingHumanInput = mapPendingHumanInput(event.data.pending_human_input);
      const meta = readStreamMeta(event.data);
      if (pendingHumanInput) {
        callbacks.onInterrupt?.({
          pendingHumanInput,
          conversationId: meta.conversationId,
          runId: meta.runId,
          agentId: meta.agentId,
        });
      }
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
