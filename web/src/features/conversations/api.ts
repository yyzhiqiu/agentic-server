import { apiRequest } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { mapPendingHumanInput } from "@/features/chat/pendingHumanInput";

import type {
  ConversationDetail,
  ConversationLatestRun,
  ConversationListResponse,
  ConversationListItem,
  ConversationMessage,
} from "@/features/conversations/types";

type BackendConversationRecord = {
  id: string;
  title: string | null;
  user_id: string | null;
  agent_id?: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

type BackendConversationMessage = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

type BackendConversationListResponse = {
  items: BackendConversationRecord[];
  total: number;
};

type BackendConversationDetail = BackendConversationRecord & {
  messages: BackendConversationMessage[];
  latest_run?: BackendConversationLatestRun | null;
};

type BackendConversationLatestRun = {
  id: string;
  agent_id: string | null;
  status: ConversationLatestRun["status"];
  interrupt_source: string | null;
  resume_available: boolean;
  pending_human_input: unknown;
  updated_at: string | null;
};

function readAgentId(record: BackendConversationRecord) {
  if (typeof record.agent_id === "string" && record.agent_id.length > 0) {
    return record.agent_id;
  }
  const metadataAgentId = record.metadata.agent_id;
  return typeof metadataAgentId === "string" && metadataAgentId.length > 0
    ? metadataAgentId
    : null;
}

function mapConversationListItem(
  record: BackendConversationRecord,
): ConversationListItem {
  return {
    id: record.id,
    title: record.title,
    userId: record.user_id,
    agentId: readAgentId(record),
    metadata: record.metadata,
    createdAt: record.created_at,
  };
}

function mapConversationMessage(
  record: BackendConversationMessage,
): ConversationMessage {
  return {
    id: record.id,
    conversationId: record.conversation_id,
    role: record.role,
    content: record.content,
    metadata: record.metadata,
    createdAt: record.created_at,
  };
}

function mapConversationLatestRun(
  record: BackendConversationLatestRun | null | undefined,
): ConversationLatestRun | null {
  if (!record) {
    return null;
  }

  return {
    id: record.id,
    agentId: record.agent_id,
    status: record.status,
    interruptSource: record.interrupt_source,
    resumeAvailable: record.resume_available,
    pendingHumanInput: mapPendingHumanInput(record.pending_human_input),
    updatedAt: record.updated_at,
  };
}

export function getConversations() {
  return apiRequest<BackendConversationListResponse>(
    API_ENDPOINTS.conversations,
  ).then<ConversationListResponse>((data) => ({
    items: data.items.map(mapConversationListItem),
    total: data.total,
  }));
}

export function getConversationDetail(conversationId: string) {
  return apiRequest<BackendConversationDetail>(
    API_ENDPOINTS.conversationDetail(conversationId),
  ).then<ConversationDetail>((data) => ({
    ...mapConversationListItem(data),
    messages: data.messages.map(mapConversationMessage),
    latestRun: mapConversationLatestRun(data.latest_run),
  }));
}
