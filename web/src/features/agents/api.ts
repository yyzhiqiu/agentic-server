import { apiRequest } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";

import type { AgentMetadata } from "@/features/agents/types";

type BackendAgentMetadata = {
  agent_id: string;
  name: string;
  description: string;
  version: string;
  capabilities: string[];
};

function mapAgentMetadata(agent: BackendAgentMetadata): AgentMetadata {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    version: agent.version,
    capabilities: agent.capabilities,
  };
}

export function getAgents() {
  return apiRequest<BackendAgentMetadata[]>(API_ENDPOINTS.agents).then(
    (data) => data.map(mapAgentMetadata),
  );
}

export function getAgent(agentId: string) {
  return apiRequest<BackendAgentMetadata>(API_ENDPOINTS.agentDetail(agentId)).then(
    mapAgentMetadata,
  );
}
