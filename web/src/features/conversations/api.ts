import { apiRequest } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";

import type {
  ConversationDetail,
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
  }));
}
