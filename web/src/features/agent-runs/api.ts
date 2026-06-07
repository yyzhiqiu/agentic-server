import type {
  AgentRunDetail,
  AgentRunListResponse,
  AgentRunListItem,
  AgentRunToolCall,
} from "@/features/agent-runs/types";
import { apiRequest } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";

type BackendAgentRunListItem = {
  id: string;
  conversation_id: string | null;
  agent_id?: string | null;
  status: AgentRunListItem["status"];
  started_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  trace_id: string | null;
  error_message: string | null;
  error_code: string | null;
  interruption_reason: string | null;
};

type BackendAgentRunToolCall = {
  id: string;
  agent_run_id: string | null;
  agent_id?: string | null;
  tool_name: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

type BackendAgentRunListResponse = {
  items: BackendAgentRunListItem[];
  total: number;
};

type BackendAgentRunDetail = BackendAgentRunListItem & {
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  metadata: Record<string, unknown>;
  tool_calls: BackendAgentRunToolCall[];
};

function readAgentId(
  value: string | null | undefined,
  metadata: Record<string, unknown> | undefined,
) {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  const metadataAgentId = metadata?.agent_id;
  return typeof metadataAgentId === "string" && metadataAgentId.length > 0
    ? metadataAgentId
    : null;
}

function mapAgentRunListItem(run: BackendAgentRunListItem): AgentRunListItem {
  return {
    id: run.id,
    conversationId: run.conversation_id,
    agentId: readAgentId(run.agent_id, undefined),
    status: run.status,
    startedAt: run.started_at,
    updatedAt: run.updated_at,
    finishedAt: run.finished_at,
    durationMs: run.duration_ms,
    traceId: run.trace_id,
    errorMessage: run.error_message,
    errorCode: run.error_code,
    interruptionReason: run.interruption_reason,
  };
}

function mapToolCall(toolCall: BackendAgentRunToolCall): AgentRunToolCall {
  return {
    id: toolCall.id,
    agentRunId: toolCall.agent_run_id,
    agentId: readAgentId(toolCall.agent_id, toolCall.metadata),
    toolName: toolCall.tool_name,
    status: toolCall.status,
    input: toolCall.input,
    output: toolCall.output,
    metadata: toolCall.metadata,
    createdAt: toolCall.created_at,
    updatedAt: toolCall.updated_at,
  };
}

export function getAgentRuns() {
  return apiRequest<BackendAgentRunListResponse>(API_ENDPOINTS.agentRuns).then<
    AgentRunListResponse
  >((data) => ({
    items: data.items.map(mapAgentRunListItem),
    total: data.total,
  }));
}

export function getAgentRunDetail(runId: string) {
  return apiRequest<BackendAgentRunDetail>(
    API_ENDPOINTS.agentRunDetail(runId),
  ).then<AgentRunDetail>((data) => ({
    ...mapAgentRunListItem(data),
    agentId: readAgentId(data.agent_id, data.metadata),
    input: data.input,
    output: data.output,
    metadata: data.metadata,
    toolCalls: data.tool_calls.map(mapToolCall),
  }));
}
