export type ChatRole = "system" | "user" | "assistant" | "tool";

export type ChatMessage = {
  id?: string;
  role: ChatRole;
  content: string;
  name?: string | null;
  metadata?: Record<string, unknown>;
};

export type ChatRequest = {
  messages: ChatMessage[];
  conversationId?: string;
  userId?: string;
  metadata?: Record<string, unknown>;
  repositoryContext?: Record<string, unknown>;
  changedFiles?: string[];
  taskType?: string | null;
};

export type ChatToolCall = {
  toolName: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type ChatResponse = {
  conversationId: string | null;
  agentId: string | null;
  message: ChatMessage;
  messages: ChatMessage[];
  metadata: Record<string, unknown>;
  toolCalls: ChatToolCall[];
};

export type ChatStreamMeta = {
  conversationId: string | null;
  runId: string | null;
  agentId: string | null;
};
