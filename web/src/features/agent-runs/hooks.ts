import { useQuery } from "@tanstack/react-query";

import { getAgentRunDetail, getAgentRuns } from "@/features/agent-runs/api";
import { QUERY_KEYS } from "@/shared/constants/query-keys";

export function useAgentRuns() {
  return useQuery({
    queryKey: QUERY_KEYS.agentRuns,
    queryFn: getAgentRuns,
  });
}

export function useAgentRunDetail(runId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.agentRunDetail(runId),
    queryFn: () => getAgentRunDetail(runId),
    enabled: Boolean(runId),
  });
}
