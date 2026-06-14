export type ChatRole = "system" | "user" | "assistant" | "tool";

export type HumanInputOption = {
  label: string;
  value: string;
};

export type HumanInputField = {
  name: string;
  label: string;
  type: "text" | "select";
  required: boolean;
  placeholder?: string | null;
  value?: string | null;
  allowCustom?: boolean;
  customOptionLabel?: string | null;
  customPlaceholder?: string | null;
  options: HumanInputOption[];
};

export type PendingHumanInput = {
  kind: "form";
  title: string;
  message: string;
  fields: HumanInputField[];
  submitLabel: string;
  missingFields: string[];
};

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

export type ChatResumeRequest = {
  runId: string;
  input: Record<string, unknown>;
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
  pendingHumanInput: PendingHumanInput | null;
};

export type ChatStreamMeta = {
  conversationId: string | null;
  runId: string | null;
  agentId: string | null;
};

export type ChatStreamMessage = {
  messageId: string;
  node: string | null;
  content: string;
  replace: boolean;
};

export type ChatStreamNodeEvent = {
  eventId: string;
  node: string;
  status: "running" | "completed";
};

export type ChatStreamToolEvent = {
  toolCallId: string;
  toolName: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type ChatInterruptPayload = {
  pendingHumanInput: PendingHumanInput;
  conversationId: string | null;
  runId: string | null;
  agentId: string | null;
};
