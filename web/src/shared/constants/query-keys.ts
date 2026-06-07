export const QUERY_KEYS = {
  conversations: ["conversations"] as const,
  conversationDetail: (conversationId: string) =>
    ["conversations", conversationId] as const,
  agentRuns: ["agent-runs"] as const,
  agentRunDetail: (runId: string) => ["agent-runs", runId] as const,
  files: ["files"] as const,
};
