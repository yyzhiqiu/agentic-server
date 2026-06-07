import { RefreshCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAgentRuns } from "@/features/agent-runs/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { LoadingState } from "@/shared/components/feedback/LoadingState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ROUTES } from "@/shared/constants/routes";
import { formatDate } from "@/shared/lib/date";

function getStatusTone(status: string) {
  if (status === "completed") {
    return "bg-emerald-100 text-emerald-800";
  }

  if (status === "running") {
    return "bg-sky-100 text-sky-800";
  }

  if (status === "interrupted") {
    return "bg-amber-100 text-amber-800";
  }

  if (status === "failed") {
    return "bg-red-100 text-red-800";
  }

  return "bg-slate-200 text-slate-700";
}

export function AgentRunsPage() {
  const navigate = useNavigate();
  const runsQuery = useAgentRuns();
  const runs = runsQuery.data?.items ?? [];
  const total = runsQuery.data?.total ?? 0;
  const runningCount = runs.filter((run) => run.status === "running").length;

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">
            Agent Runs
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            Agent 运行记录
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            这里展示运行状态、Agent、耗时、Trace 和详情入口，便于查看不同智能体的执行历史。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void runsQuery.refetch();
          }}
          disabled={runsQuery.isFetching}
          className="gap-2"
        >
          <RefreshCcw
            size={16}
            className={runsQuery.isFetching ? "animate-spin" : ""}
          />
          刷新列表
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <p className="text-sm text-slate-500">运行总数</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">{total}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">运行中</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">
            {runningCount}
          </p>
        </Card>
      </div>

      {runsQuery.isLoading ? <LoadingState title="正在加载运行记录..." /> : null}

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
          title="还没有运行记录"
          description="发起聊天或任务后，这里会展示每次 Agent 执行的历史记录。"
        />
      ) : null}

      {!runsQuery.isLoading && !runsQuery.isError && total > 0 ? (
        <div className="grid gap-4">
          {runs.map((run) => (
            <Card key={run.id} className="space-y-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold text-slate-900">
                    运行 {run.id}
                  </h2>
                  <p className="mt-1 break-all text-sm text-slate-500">
                    会话 ID: {run.conversationId ?? "未关联"}
                  </p>
                </div>
                <Badge className={getStatusTone(run.status)}>
                  状态: {run.status}
                </Badge>
              </div>

              <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-2 lg:grid-cols-5">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    Agent
                  </p>
                  <p className="mt-1 break-all text-slate-700">
                    {run.agentId ?? "未知"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    开始时间
                  </p>
                  <p className="mt-1 text-slate-700">
                    {run.startedAt ? formatDate(run.startedAt) : "暂无"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    结束时间
                  </p>
                  <p className="mt-1 text-slate-700">
                    {run.finishedAt ? formatDate(run.finishedAt) : "运行中"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    耗时
                  </p>
                  <p className="mt-1 text-slate-700">
                    {run.durationMs !== null ? `${run.durationMs} ms` : "暂无"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    Trace ID
                  </p>
                  <p className="mt-1 break-all text-slate-700">
                    {run.traceId ?? "暂无"}
                  </p>
                </div>
              </div>

              {run.errorMessage ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  失败原因: {run.errorMessage}
                  {run.errorCode ? ` (${run.errorCode})` : ""}
                </div>
              ) : null}

              {run.interruptionReason ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  中断原因: {run.interruptionReason}
                </div>
              ) : null}

              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={() => {
                    navigate(`${ROUTES.agentRuns}/${run.id}`);
                  }}
                >
                  查看详情
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
