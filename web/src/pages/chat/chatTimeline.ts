import type {
  ChatMessage as ApiChatMessage,
  ChatResponse,
  PendingHumanInput,
} from "@/features/chat/types";
import type { ConversationMessage } from "@/features/conversations/types";
import { createId } from "@/shared/lib/id";

export type TimelineMessage = ApiChatMessage & {
  id: string;
  pending?: boolean;
};

export type RenderMessage = {
  id: string;
  role: string;
  content: string;
  pending?: boolean;
  metadata?: Record<string, unknown>;
  name?: string | null;
};

function normalizeRole(role: string): ApiChatMessage["role"] {
  if (
    role === "system" ||
    role === "assistant" ||
    role === "tool" ||
    role === "user"
  ) {
    return role;
  }
  return "user";
}

function readMetadataString(
  metadata: Record<string, unknown> | undefined,
  key: string,
) {
  const value = metadata?.[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function buildStableMessageId(
  message: {
    id?: string;
    role: string;
    content: string;
    metadata?: Record<string, unknown>;
  },
  index: number,
  prefix: string,
) {
  const metadataId =
    readMetadataString(message.metadata, "message_id") ??
    readMetadataString(message.metadata, "id");
  if (metadataId) {
    return metadataId;
  }

  if (message.id) {
    return message.id;
  }

  const contentPart = message.content.slice(0, 32).replace(/\s+/g, "-");
  return `${prefix}-${index}-${message.role}-${contentPart || "empty"}`;
}

function areMessagesEqual(left: ApiChatMessage, right: ApiChatMessage) {
  return (
    left.role === right.role &&
    left.content === right.content &&
    (left.name ?? null) === (right.name ?? null)
  );
}

function toTimelineMessage(
  message: ApiChatMessage,
  index: number,
  prefix: string,
): TimelineMessage {
  return {
    ...message,
    id: buildStableMessageId(message, index, prefix),
    pending: false,
  };
}

export function conversationMessagesToTimeline(
  messages: ConversationMessage[],
): TimelineMessage[] {
  return messages.map((message, index) => ({
    id: message.id || buildStableMessageId(message, index, "history"),
    role: normalizeRole(message.role),
    content: message.content,
    metadata: message.metadata,
    pending: false,
  }));
}

export function createLocalTimelineMessage(
  message: ApiChatMessage,
  prefix = "local",
): TimelineMessage {
  return {
    ...message,
    id: message.id ?? createId(prefix),
    pending: false,
  };
}

export function toRenderMessages(messages: TimelineMessage[]): RenderMessage[] {
  return messages.map((message) => ({
    id: message.id,
    role: message.role,
    content: message.content,
    pending: message.pending,
    metadata: message.metadata,
    name: message.name,
  }));
}

export function mergeTimelineWithResponse(
  currentMessages: TimelineMessage[],
  responseMessages: ApiChatMessage[],
): TimelineMessage[] {
  const current = currentMessages.filter((message) => !message.pending);
  if (responseMessages.length === 0) {
    return current;
  }

  const responseTimeline = responseMessages.map((message, index) =>
    toTimelineMessage(message, index, "response"),
  );
  if (current.length === 0) {
    return responseTimeline;
  }

  const maxOverlap = Math.min(current.length, responseTimeline.length);
  for (let size = maxOverlap; size > 0; size -= 1) {
    const currentSlice = current.slice(current.length - size);
    const responseSlice = responseTimeline.slice(0, size);
    if (
      currentSlice.every((message, index) =>
        areMessagesEqual(message, responseSlice[index]),
      )
    ) {
      return [...current, ...responseTimeline.slice(size)];
    }
  }

  const latestCurrent = current[current.length - 1];
  const unseenResponse = responseTimeline.filter(
    (responseMessage) => !areMessagesEqual(latestCurrent, responseMessage),
  );
  return [...current, ...unseenResponse];
}

export function upsertStreamingAssistantMessage(
  currentMessages: TimelineMessage[],
  streamMessageId: string,
  content: string,
): TimelineMessage[] {
  const existingIndex = currentMessages.findIndex(
    (message) => message.id === streamMessageId,
  );
  const nextMessage: TimelineMessage = {
    id: streamMessageId,
    role: "assistant",
    content,
    pending: true,
  };

  if (existingIndex < 0) {
    return [...currentMessages, nextMessage];
  }

  return currentMessages.map((message, index) =>
    index === existingIndex ? nextMessage : message,
  );
}

export function removeStreamingAssistantMessage(
  currentMessages: TimelineMessage[],
  streamMessageId: string | null,
): TimelineMessage[] {
  if (!streamMessageId) {
    return currentMessages;
  }
  return currentMessages.filter((message) => message.id !== streamMessageId);
}

export function buildResumeMessage(
  input: Record<string, string>,
  pendingHumanInput: PendingHumanInput | null,
): ApiChatMessage | null {
  const labelMap = new Map(
    (pendingHumanInput?.fields ?? []).map((field) => [field.name, field.label]),
  );
  const parts = Object.entries(input)
    .map(([key, value]) => {
      const normalizedValue = value.trim();
      if (!normalizedValue) {
        return null;
      }
      return `${labelMap.get(key) ?? key}：${normalizedValue}`;
    })
    .filter((part): part is string => part !== null);

  if (parts.length === 0) {
    return null;
  }

  return {
    role: "user",
    content: `补充路线规划信息：${parts.join("；")}`,
    metadata: {
      messageType: "human_input_resume",
      resumeInput: { ...input },
    },
  };
}

export function applyResumeMessageToResponse(
  response: ChatResponse,
  resumeMessage: ApiChatMessage | null,
): ChatResponse {
  if (!resumeMessage) {
    return response;
  }

  const alreadyIncluded = response.messages.some((message) =>
    areMessagesEqual(message, resumeMessage),
  );
  if (alreadyIncluded) {
    return response;
  }

  const nextMessages = [...response.messages];
  let assistantIndex = -1;
  for (let index = nextMessages.length - 1; index >= 0; index -= 1) {
    const message = nextMessages[index];
    if (message.role === "assistant") {
      assistantIndex = index;
      break;
    }
  }
  if (assistantIndex >= 0) {
    nextMessages.splice(assistantIndex, 0, resumeMessage);
  } else {
    nextMessages.push(resumeMessage);
  }

  return {
    ...response,
    messages: nextMessages,
  };
}
