export const QUERY_KEYS = {
  agents: ["agents"] as const,
  agentDetail: (agentId: string) => ["agents", agentId] as const,
  conversations: ["conversations"] as const,
  conversationDetail: (conversationId: string) =>
    ["conversations", conversationId] as const,
  agentRuns: ["agent-runs"] as const,
  agentRunDetail: (runId: string) => ["agent-runs", runId] as const,
  files: ["files"] as const,
};
