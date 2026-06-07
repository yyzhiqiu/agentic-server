export type AgentRunStatus =
  | "running"
  | "interrupted"
  | "cancelled"
  | "completed"
  | "failed"
  | "created";

export type AgentRunToolCall = {
  id: string;
  agentRunId: string | null;
  agentId: string | null;
  toolName: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt: string | null;
  updatedAt: string | null;
};

export type AgentRunListItem = {
  id: string;
  conversationId: string | null;
  agentId: string | null;
  status: AgentRunStatus;
  startedAt: string | null;
  updatedAt: string | null;
  finishedAt: string | null;
  durationMs: number | null;
  traceId: string | null;
  errorMessage: string | null;
  errorCode: string | null;
  interruptionReason: string | null;
};

export type AgentRunListResponse = {
  items: AgentRunListItem[];
  total: number;
};

export type AgentRunDetail = AgentRunListItem & {
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
  toolCalls: AgentRunToolCall[];
};
