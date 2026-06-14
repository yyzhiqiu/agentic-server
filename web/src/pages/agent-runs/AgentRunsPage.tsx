import { RefreshCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAgentRuns } from "@/features/agent-runs/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ROUTES } from "@/shared/constants/routes";
import { formatDate } from "@/shared/lib/date";

function getBadgeVariant(status: string): "default" | "success" | "warning" | "info" | "destructive" | "secondary" {
  if (status === "completed") return "success";
  if (status === "running") return "info";
  if (status === "interrupted") return "warning";
  if (status === "cancelled") return "secondary";
  if (status === "failed") return "destructive";
  return "default";
}

export function AgentRunsPage() {
  const navigate = useNavigate();
  const runsQuery = useAgentRuns();
  const runs = runsQuery.data?.items ?? [];
  const total = runsQuery.data?.total ?? 0;
  const runningCount = runs.filter((run) => run.status === "running").length;

  return (
    <section className="h-full overflow-y-auto pr-2 space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between select-none">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            监控智能体每次调用的运行状态。包含开始与结束时间、执行耗时、以及可视化 Trace 分析入口。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void runsQuery.refetch();
          }}
          disabled={runsQuery.isFetching}
          className="gap-2 self-start lg:self-auto text-xs"
        >
          <RefreshCcw
            size={14}
            className={runsQuery.isFetching ? "animate-spin" : ""}
          />
          <span>刷新列表</span>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 max-w-lg select-none">
        <Card className="border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-5">
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">运行任务总数</p>
          <p className="mt-2 text-3xl font-extrabold text-slate-900 dark:text-slate-100 font-display">{total}</p>
        </Card>
        <Card className="border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-5">
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">当前运行中</p>
          <p className="mt-2 text-3xl font-extrabold text-brand-700 dark:text-brand-400 font-display">
            {runningCount}
          </p>
        </Card>
      </div>

      {runsQuery.isLoading ? (
        <Card className="flex items-center justify-center p-8">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
            </span>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">正在加载运行记录...</p>
          </div>
        </Card>
      ) : null}

      {runsQuery.isError ? (
        <div className="space-y-3">
          <ErrorState message={runsQuery.error.message} />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void runsQuery.refetch();
            }}
          >
            重新加载
          </Button>
        </div>
      ) : null}

      {!runsQuery.isLoading && !runsQuery.isError && total === 0 ? (
        <EmptyState
          title="暂无运行记录"
          description="发起多智能体对话或规划任务后，此页将自动更新并追加相应的执行生命周期历史记录。"
        />
      ) : null}

      {!runsQuery.isLoading && !runsQuery.isError && total > 0 ? (
        <div className="grid gap-4">
          {runs.map((run) => (
            <Card
              key={run.id}
              className="space-y-4 border border-slate-200 bg-white/70 dark:border-slate-800/80 dark:bg-slate-900/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between border-b border-slate-100 dark:border-slate-800/50 pb-3">
                <div className="min-w-0">
                  <h2 className="truncate text-base font-bold text-slate-900 dark:text-slate-100 font-display">
                    运行 ID: <span className="font-mono text-xs">{run.id}</span>
                  </h2>
                  <p className="mt-1 break-all text-xs font-mono text-slate-400 dark:text-slate-500">
                    关联会话: {run.conversationId ?? "未关联会话"}
                  </p>
                </div>
                <Badge variant={getBadgeVariant(run.status)} className="self-start lg:self-auto shrink-0 uppercase text-[9px] tracking-wider">
                  {run.status}
                </Badge>
              </div>

              <div className="grid gap-4 text-xs md:grid-cols-2 lg:grid-cols-5">
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    触发 Agent
                  </p>
                  <p className="mt-1 break-all text-slate-700 dark:text-slate-300 font-mono">
                    {run.agentId ?? "未知"}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    开始时间
                  </p>
                  <p className="mt-1 text-slate-700 dark:text-slate-300">
                    {run.startedAt ? formatDate(run.startedAt) : "暂无记录"}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    结束时间
                  </p>
                  <p className="mt-1 text-slate-700 dark:text-slate-300">
                    {run.finishedAt ? formatDate(run.finishedAt) : <span className="text-brand-500 animate-pulse font-medium">运行中</span>}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    任务耗时
                  </p>
                  <p className="mt-1 text-slate-700 dark:text-slate-300 font-mono">
                    {run.durationMs !== null ? `${run.durationMs} ms` : "---"}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    Trace ID
                  </p>
                  <p className="mt-1 break-all text-slate-700 dark:text-slate-300 font-mono font-semibold">
                    {run.traceId ?? "暂无"}
                  </p>
                </div>
              </div>

              {run.errorMessage ? (
                <div className="rounded-2xl border border-red-200 bg-red-50/50 dark:border-red-950/20 dark:bg-red-950/15 px-4 py-3 text-xs text-red-700 dark:text-red-400">
                  <span className="font-bold">异常中断:</span> {run.errorMessage}
                  {run.errorCode ? ` [Code: ${run.errorCode}]` : ""}
                </div>
              ) : null}

              {run.interruptionReason ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50/50 dark:border-amber-950/20 dark:bg-amber-950/15 px-4 py-3 text-xs text-amber-800 dark:text-amber-400">
                  <span className="font-bold">挂起原因:</span> {run.interruptionReason}
                </div>
              ) : null}

              <div className="flex justify-end pt-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    navigate(`${ROUTES.agentRuns}/${run.id}`);
                  }}
                  className="text-xs font-semibold px-4 py-1.5"
                >
                  查看运行详情
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
