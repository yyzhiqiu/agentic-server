import type { AgentMetadata } from "@/features/agents/types";
import { Badge } from "@/shared/components/ui/badge";

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
      <div className="space-y-2 p-1">
        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">智能体选择</p>
        <p className="text-sm text-slate-500 dark:text-slate-400">正在加载可用智能体...</p>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="space-y-2 p-4 border border-amber-250 bg-amber-50/10 dark:border-amber-900/40 dark:bg-amber-950/10 rounded-2xl">
        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">智能体选择</p>
        <p className="text-sm text-amber-700 dark:text-amber-400 font-medium">
          智能体列表加载失败，当前将回退到默认 `chat_agent`，你仍然可以继续聊天。
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{errorMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-1">
      <div className="flex flex-wrap items-center justify-between gap-3 select-none">
        <div>
          <p className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">智能体选择</p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            切换智能体会自动重置当前会话，确保各 Agent 逻辑环境隔离。
          </p>
        </div>
        <Badge variant="default">{agents.length} Agents</Badge>
      </div>

      <div className="flex flex-col gap-3">
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
              className={`rounded-xl border p-3 text-left transition-all duration-300 ${
                isActive
                  ? "border-brand-600 bg-brand-50/50 shadow-sm dark:border-brand-500 dark:bg-brand-950/20"
                  : "border-slate-200/80 bg-slate-50/50 hover:border-brand-300 hover:bg-white dark:border-slate-800/80 dark:bg-slate-950/20 dark:hover:border-slate-700/80 dark:hover:bg-slate-950/50"
              } ${disabled ? "cursor-not-allowed opacity-60" : "active:scale-[0.98]"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">{agent.name}</p>
                  <p className="mt-0.5 text-[9px] uppercase font-semibold tracking-wider text-slate-400 dark:text-slate-500 truncate font-mono">
                    {agent.agentId}
                  </p>
                </div>
                <Badge variant={isActive ? "default" : "secondary"} className="shrink-0 text-[10px]">
                  {isActive ? "运行中" : agent.version}
                </Badge>
              </div>
              <p className="mt-1.5 text-[11px] leading-normal text-slate-500 dark:text-slate-450 line-clamp-2">{agent.description}</p>
              <p className="mt-2 text-[9px] font-semibold text-slate-400 dark:text-slate-550 border-t border-slate-100/50 dark:border-slate-800/40 pt-1.5 truncate">
                能力：{renderCapabilities(agent)}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
