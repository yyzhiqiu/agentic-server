import type { AgentMetadata } from "@/features/agents/types";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";

type AgentSelectorProps = {
  agents: AgentMetadata[];
  selectedAgentId: string;
  disabled?: boolean;
  loading?: boolean;
  errorMessage?: string | null;
  onSelect: (agentId: string) => void;
};

function renderCapabilities(agent: AgentMetadata) {
  if (agent.capabilities.length === 0) {
    return "暂无能力标签";
  }
  return agent.capabilities.join(" · ");
}

export function AgentSelector({
  agents,
  selectedAgentId,
  disabled = false,
  loading = false,
  errorMessage = null,
  onSelect,
}: AgentSelectorProps) {
  if (loading) {
    return (
      <Card className="space-y-2">
        <p className="text-sm font-semibold text-slate-900">智能体选择</p>
        <p className="text-sm text-slate-500">正在加载可用智能体...</p>
      </Card>
    );
  }

  if (errorMessage) {
    return (
      <Card className="space-y-2">
        <p className="text-sm font-semibold text-slate-900">智能体选择</p>
        <p className="text-sm text-amber-700">
          智能体列表加载失败，当前将回退到默认 `chat_agent`，你仍然可以继续聊天。
        </p>
        <p className="text-xs text-slate-500">{errorMessage}</p>
      </Card>
    );
  }

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">智能体选择</p>
          <p className="mt-1 text-sm text-slate-500">
            切换智能体会开启新会话，避免把同一段历史混给不同 Agent。
          </p>
        </div>
        <Badge>{agents.length} Agents</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {agents.map((agent) => {
          const isActive = agent.agentId === selectedAgentId;
          return (
            <button
              key={agent.agentId}
              type="button"
              disabled={disabled}
              onClick={() => {
                onSelect(agent.agentId);
              }}
              className={`rounded-3xl border p-4 text-left transition ${
                isActive
                  ? "border-brand-700 bg-brand-50 shadow-sm"
                  : "border-slate-200 bg-slate-50/70 hover:border-brand-300 hover:bg-white"
              } ${disabled ? "cursor-not-allowed opacity-70" : ""}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-slate-900">{agent.name}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">
                    {agent.agentId}
                  </p>
                </div>
                <Badge className={isActive ? "bg-brand-700 text-white" : ""}>
                  {isActive ? "当前使用" : agent.version}
                </Badge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{agent.description}</p>
              <p className="mt-3 text-xs leading-5 text-slate-500">
                {renderCapabilities(agent)}
              </p>
            </button>
          );
        })}
      </div>

      <div className="flex justify-end">
        <Button
          variant="secondary"
          size="sm"
          disabled
        >
          已按当前智能体路由
        </Button>
      </div>
    </Card>
  );
}
