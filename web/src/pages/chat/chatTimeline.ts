import type {
  ChatMessage as ApiChatMessage,
  ChatResponse,
  ChatStreamMeta,
  ChatStreamNodeEvent,
  ChatStreamToolEvent,
  PendingHumanInput,
} from "@/features/chat/types";
import type { AgentRunDetail } from "@/features/agent-runs/types";
import type {
  ConversationMessage,
  ConversationRunTrace,
} from "@/features/conversations/types";
import { createId } from "@/shared/lib/id";

export type AgentExecutionActivity = {
  id: string;
  kind: "agent";
  sourceAgentId: string | null;
  targetAgentId: string;
  status:
    | "created"
    | "running"
    | "interrupted"
    | "cancelled"
    | "completed"
    | "failed";
  reason: string | null;
  details: Record<string, unknown>;
};

export type ToolExecutionActivity = {
  id: string;
  kind: "tool";
  toolName: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type NodeExecutionActivity = {
  id: string;
  kind: "node";
  nodeName: string;
  status: "running" | "completed" | "failed";
};

export type ExecutionActivity =
  | AgentExecutionActivity
  | NodeExecutionActivity
  | ToolExecutionActivity;

export type TimelineMessage = ApiChatMessage & {
  id: string;
  pending?: boolean;
  activities?: ExecutionActivity[];
};

export type RenderMessage = {
  id: string;
  role: string;
  content: string;
  pending?: boolean;
  activities?: ExecutionActivity[];
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

function readRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function buildHistoryActivities(
  message: ConversationMessage,
  runTrace: ConversationRunTrace | null,
): ExecutionActivity[] {
  if (message.role !== "assistant") {
    return [];
  }

  const targetAgentId =
    runTrace?.agentId ?? readMetadataString(message.metadata, "agent_id");
  if (!targetAgentId) {
    return [];
  }

  const traceMetadata = runTrace?.metadata ?? message.metadata;
  const sourceAgentId = readMetadataString(traceMetadata, "routed_by");
  const routeDecision = readRecord(traceMetadata.route_decision);
  const activities: ExecutionActivity[] = [
    {
      id: `${runTrace?.id ?? message.id}-agent`,
      kind: "agent",
      sourceAgentId,
      targetAgentId,
      status: runTrace?.status ?? "completed",
      reason:
        routeDecision && typeof routeDecision.reason === "string"
          ? routeDecision.reason
          : null,
      details: {
        ...(routeDecision ? { route_decision: routeDecision } : {}),
        ...(runTrace ? { run_id: runTrace.id } : {}),
      },
    },
  ];
  runTrace?.toolCalls.forEach((toolCall) => {
    activities.push({
      id: toolCall.id,
      kind: "tool",
      toolName: toolCall.toolName,
      status: toolCall.status,
      input: toolCall.input,
      output: toolCall.output,
      metadata: toolCall.metadata,
    });
  });
  return activities;
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
  runTraces: ConversationRunTrace[] = [],
): TimelineMessage[] {
  const usedRunIds = new Set<string>();
  return messages.map((message, index) => {
    const messageId = readMetadataString(message.metadata, "message_id");
    const runTrace =
      message.role === "assistant"
        ? runTraces.find(
            (trace) =>
              !usedRunIds.has(trace.id) &&
              ((messageId &&
                trace.assistantMessageId === messageId) ||
                (!trace.assistantMessageId &&
                  trace.assistantContent === message.content)),
          ) ?? null
        : null;
    if (runTrace) {
      usedRunIds.add(runTrace.id);
    }

    return {
      id: message.id || buildStableMessageId(message, index, "history"),
      role: normalizeRole(message.role),
      content: message.content,
      metadata: message.metadata,
      pending: false,
      activities: buildHistoryActivities(message, runTrace),
    };
  });
}

export function mergeConversationHistoryWithTimeline(
  messages: ConversationMessage[],
  currentMessages: TimelineMessage[],
  runTraces: ConversationRunTrace[] = [],
): TimelineMessage[] {
  const historyMessages = conversationMessagesToTimeline(messages, runTraces);
  const matchedIndexes = new Set<number>();

  return historyMessages.map((historyMessage) => {
    let matchedIndex = currentMessages.findIndex(
      (currentMessage, index) =>
        !matchedIndexes.has(index) && currentMessage.id === historyMessage.id,
    );

    if (matchedIndex < 0) {
      matchedIndex = currentMessages.findIndex(
        (currentMessage, index) =>
          !matchedIndexes.has(index) &&
          areMessagesEqual(currentMessage, historyMessage),
      );
    }

    if (matchedIndex < 0) {
      return historyMessage;
    }

    matchedIndexes.add(matchedIndex);
    const currentMessage = currentMessages[matchedIndex];
    return {
      ...historyMessage,
      activities:
        currentMessage.activities && currentMessage.activities.length > 0
          ? currentMessage.activities
          : historyMessage.activities,
    };
  });
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
    activities: message.activities,
  }));
}

export function buildRunningExecutionActivities(
  meta: ChatStreamMeta,
  requestedAgentId: string | null,
): ExecutionActivity[] {
  const targetAgentId = meta.agentId ?? requestedAgentId;
  if (!targetAgentId) {
    return [];
  }

  return [
    {
      id: `${meta.runId ?? "pending-run"}-agent`,
      kind: "agent",
      sourceAgentId: requestedAgentId,
      targetAgentId,
      status: "running",
      reason: null,
      details: {
        conversation_id: meta.conversationId,
        run_id: meta.runId,
      },
    },
  ];
}

export function buildResponseExecutionActivities(
  response: ChatResponse,
  requestedAgentId: string | null,
): ExecutionActivity[] {
  const activities: ExecutionActivity[] = [];
  const routeDecision = readRecord(response.metadata.route_decision);
  const routedBy =
    readMetadataString(response.metadata, "routed_by") ?? requestedAgentId;
  const targetAgentId =
    response.agentId ?? readMetadataString(response.metadata, "agent_id");

  if (targetAgentId) {
    activities.push({
      id: `${readRunId(response.metadata) ?? "response"}-agent`,
      kind: "agent",
      sourceAgentId: routedBy,
      targetAgentId,
      status: response.pendingHumanInput ? "interrupted" : "completed",
      reason:
        routeDecision && typeof routeDecision.reason === "string"
          ? routeDecision.reason
          : null,
      details: {
        ...(routeDecision ? { route_decision: routeDecision } : {}),
        run_id: readRunId(response.metadata),
        routed_by: readMetadataString(response.metadata, "routed_by"),
      },
    });
  }

  response.toolCalls.forEach((toolCall, index) => {
    const toolCallId = readMetadataString(toolCall.metadata, "tool_call_id");
    activities.push({
      id: toolCallId ?? `tool-${index}-${toolCall.toolName}`,
      kind: "tool",
      toolName: toolCall.toolName,
      status: toolCall.status,
      input: toolCall.input,
      output: toolCall.output,
      metadata: toolCall.metadata,
    });
  });

  return activities;
}

export function buildAgentRunExecutionActivities(
  run: AgentRunDetail,
): ExecutionActivity[] {
  const outputMetadata = readRecord(run.output.metadata) ?? {};
  const routeDecision = readRecord(outputMetadata.route_decision);
  const sourceAgentId =
    readMetadataString(outputMetadata, "routed_by") ??
    readMetadataString(run.metadata, "graph_agent_id");
  const targetAgentId =
    run.agentId ?? readMetadataString(outputMetadata, "agent_id");
  const activities: ExecutionActivity[] = [];

  if (targetAgentId) {
    activities.push({
      id: `${run.id}-agent`,
      kind: "agent",
      sourceAgentId,
      targetAgentId,
      status: run.status,
      reason:
        routeDecision && typeof routeDecision.reason === "string"
          ? routeDecision.reason
          : null,
      details: {
        ...(routeDecision ? { route_decision: routeDecision } : {}),
        run_id: run.id,
        routed_by: sourceAgentId,
      },
    });
  }

  run.toolCalls.forEach((toolCall) => {
    activities.push({
      id: toolCall.id,
      kind: "tool",
      toolName: toolCall.toolName,
      status: toolCall.status,
      input: toolCall.input,
      output: toolCall.output,
      metadata: toolCall.metadata,
    });
  });

  return activities;
}

export function attachActivitiesToLatestAssistant(
  messages: TimelineMessage[],
  activities: ExecutionActivity[],
): TimelineMessage[] {
  if (activities.length === 0) {
    return messages;
  }

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === "assistant") {
      return messages.map((message, messageIndex) =>
        messageIndex === index ? { ...message, activities } : message,
      );
    }
  }
  return messages;
}

function updateTraceActivities(
  messages: TimelineMessage[],
  traceMessageId: string,
  update: (activities: ExecutionActivity[]) => ExecutionActivity[],
): TimelineMessage[] {
  return messages.map((message) =>
    message.id === traceMessageId
      ? {
          ...message,
          activities: update(message.activities ?? []),
        }
      : message,
  );
}

export function upsertStreamingNodeActivity(
  messages: TimelineMessage[],
  traceMessageId: string,
  event: ChatStreamNodeEvent,
): TimelineMessage[] {
  return updateTraceActivities(messages, traceMessageId, (activities) => {
    const id = `node-${event.eventId}`;
    const nextActivity: NodeExecutionActivity = {
      id,
      kind: "node",
      nodeName: event.node,
      status: event.status,
    };
    const existingIndex = activities.findIndex(
      (activity) => activity.id === id,
    );
    if (existingIndex < 0) {
      return [...activities, nextActivity];
    }
    return activities.map((activity, index) =>
      index === existingIndex ? nextActivity : activity,
    );
  });
}

export function upsertStreamingToolActivity(
  messages: TimelineMessage[],
  traceMessageId: string,
  event: ChatStreamToolEvent,
): TimelineMessage[] {
  return updateTraceActivities(messages, traceMessageId, (activities) => {
    const id = `tool-${event.toolCallId}`;
    const nextActivity: ToolExecutionActivity = {
      id,
      kind: "tool",
      toolName: event.toolName,
      status: event.status,
      input: event.input,
      output: event.output,
      metadata: event.metadata,
    };
    const existingIndex = activities.findIndex(
      (activity) => activity.id === id,
    );
    if (existingIndex < 0) {
      return [...activities, nextActivity];
    }
    return activities.map((activity, index) =>
      index === existingIndex ? nextActivity : activity,
    );
  });
}

function readRunId(metadata: Record<string, unknown>) {
  return readMetadataString(metadata, "run_id");
}

function findLatestPendingActivities(
  messages: TimelineMessage[],
): ExecutionActivity[] {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].pending) {
      return messages[index].activities ?? [];
    }
  }
  return [];
}

export function mergeTimelineWithResponse(
  currentMessages: TimelineMessage[],
  responseMessages: ApiChatMessage[],
  activities: ExecutionActivity[] = [],
): TimelineMessage[] {
  const streamingActivities = findLatestPendingActivities(currentMessages);
  const finalActivities =
    activities.length > 0
      ? activities
      : streamingActivities.map((activity) =>
          activity.kind === "agent"
            ? { ...activity, status: "completed" as const }
            : activity,
        );
  const current = currentMessages.filter((message) => !message.pending);
  if (responseMessages.length === 0) {
    for (let index = current.length - 1; index >= 0; index -= 1) {
      if (current[index].role === "assistant") {
        return current.map((message, messageIndex) =>
          messageIndex === index
            ? { ...message, activities: finalActivities }
            : message,
        );
      }
    }
    return current;
  }

  const responseTimeline = responseMessages.map((message, index) =>
    toTimelineMessage(message, index, "response"),
  );
  for (let index = responseTimeline.length - 1; index >= 0; index -= 1) {
    if (responseTimeline[index].role === "assistant") {
      responseTimeline[index] = {
        ...responseTimeline[index],
        activities: finalActivities,
      };
      break;
    }
  }
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
  activities?: ExecutionActivity[],
): TimelineMessage[] {
  const existingIndex = currentMessages.findIndex(
    (message) => message.id === streamMessageId,
  );
  const nextMessage: TimelineMessage = {
    id: streamMessageId,
    role: "assistant",
    content,
    pending: true,
    activities:
      activities ??
      (existingIndex >= 0
        ? currentMessages[existingIndex].activities
        : undefined),
  };

  if (existingIndex < 0) {
    return [...currentMessages, nextMessage];
  }

  return currentMessages.map((message, index) =>
    index === existingIndex ? nextMessage : message,
  );
}

export function failStreamingAssistantMessage(
  currentMessages: TimelineMessage[],
  streamMessageId: string | null,
): TimelineMessage[] {
  if (!streamMessageId) {
    return currentMessages;
  }

  return currentMessages.map((message) => {
    const belongsToStream =
      message.id === streamMessageId ||
      message.id.startsWith(`${streamMessageId}-`);
    if (!belongsToStream) {
      return message;
    }

    return {
      ...message,
      content:
        message.content === "等待流式响应中..." ? "" : message.content,
      pending: false,
      activities: (message.activities ?? []).map((activity) =>
        activity.status === "running"
          ? { ...activity, status: "failed" as const }
          : activity,
      ),
    };
  });
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
