import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  cancelAgentRun,
  getAgentRunDetail,
  getAgentRuns,
  interruptAgentRun,
  resumeAgentRun,
} from "@/features/agent-runs/api";
import { QUERY_KEYS } from "@/shared/constants/query-keys";

type AgentRunControlVariables = {
  runId: string;
  agentId?: string | null;
  reason?: string;
  input?: Record<string, unknown>;
};

async function invalidateAgentRunQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  runId: string,
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agentRuns }),
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.agentRunDetail(runId),
    }),
  ]);
}

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

export function useResumeAgentRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: AgentRunControlVariables) =>
      resumeAgentRun(variables.runId, variables.agentId, variables.input),
    onSuccess: async (_data, variables) => {
      await invalidateAgentRunQueries(queryClient, variables.runId);
    },
  });
}

export function useInterruptAgentRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: AgentRunControlVariables) =>
      interruptAgentRun(variables.runId, variables.agentId, variables.reason),
    onSuccess: async (_data, variables) => {
      await invalidateAgentRunQueries(queryClient, variables.runId);
    },
  });
}

export function useCancelAgentRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: AgentRunControlVariables) =>
      cancelAgentRun(variables.runId, variables.agentId, variables.reason),
    onSuccess: async (_data, variables) => {
      await invalidateAgentRunQueries(queryClient, variables.runId);
    },
  });
}
