export type AgentCapability = string;

export type AgentMetadata = {
  agentId: string;
  name: string;
  description: string;
  version: string;
  capabilities: AgentCapability[];
};
