import { useQuery } from "@tanstack/react-query";

import { getAgent, getAgents } from "@/features/agents/api";
import { QUERY_KEYS } from "@/shared/constants/query-keys";

export function useAgents() {
  return useQuery({
    queryKey: QUERY_KEYS.agents,
    queryFn: getAgents,
  });
}

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.agentDetail(agentId),
    queryFn: () => getAgent(agentId),
    enabled: Boolean(agentId),
  });
}
