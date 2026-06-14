import type { PendingHumanInput } from "@/features/chat/types";
import type {
  AgentRunStatus,
  AgentRunToolCall,
} from "@/features/agent-runs/types";

export type ConversationMetadata = Record<string, unknown>;

export type ConversationMessage = {
  id: string;
  conversationId: string;
  role: string;
  content: string;
  metadata: ConversationMetadata;
  createdAt: string | null;
};

export type ConversationLatestRun = {
  id: string;
  agentId: string | null;
  status:
    | "running"
    | "interrupted"
    | "cancelled"
    | "completed"
    | "failed"
    | "created";
  interruptSource: string | null;
  resumeAvailable: boolean;
  pendingHumanInput: PendingHumanInput | null;
  updatedAt: string | null;
};

export type ConversationRunTrace = {
  id: string;
  agentId: string | null;
  status: AgentRunStatus;
  assistantMessageId: string | null;
  assistantContent: string | null;
  metadata: ConversationMetadata;
  toolCalls: AgentRunToolCall[];
};

export type ConversationListItem = {
  id: string;
  title: string | null;
  userId: string | null;
  agentId: string | null;
  metadata: ConversationMetadata;
  createdAt: string | null;
};

export type ConversationListResponse = {
  items: ConversationListItem[];
  total: number;
};

export type ConversationDetail = ConversationListItem & {
  messages: ConversationMessage[];
  latestRun: ConversationLatestRun | null;
  runTraces: ConversationRunTrace[];
};
