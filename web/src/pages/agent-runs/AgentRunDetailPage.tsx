import { useState } from "react";
import { useParams } from "react-router-dom";

import {
  useAgentRunDetail,
  useCancelAgentRun,
  useInterruptAgentRun,
  useResumeAgentRun,
} from "@/features/agent-runs/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { formatDate } from "@/shared/lib/date";

function getBadgeVariant(status: string): "default" | "success" | "warning" | "info" | "destructive" | "secondary" {
  if (status === "completed") return "success";
  if (status === "running") return "info";
  if (status === "interrupted") return "warning";
  if (status === "cancelled") return "secondary";
  if (status === "failed") return "destructive";
  return "default";
}

function renderJson(value: Record<string, unknown>) {
  const keys = Object.keys(value);
  if (keys.length === 0) {
    return "暂无";
  }

  return JSON.stringify(value, null, 2);
}

function getControlErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "操作失败，请稍后重试。";
}

export function AgentRunDetailPage() {
  const { runId } = useParams();
  const runQuery = useAgentRunDetail(runId ?? "");
  const resumeMutation = useResumeAgentRun();
  const interruptMutation = useInterruptAgentRun();
  const cancelMutation = useCancelAgentRun();
  const [actionFeedback, setActionFeedback] = useState<{
    tone: "success" | "error";
    message: string;
  } | null>(null);

  const run = runQuery.data;
  const isActionPending =
    resumeMutation.isPending ||
    interruptMutation.isPending ||
    cancelMutation.isPending;
  const canResume =
    run?.status === "interrupted" &&
    run.metadata.resume_available !== false;
  const canInterrupt = run?.status === "running";
  const canCancel =
    run?.status === "running" ||
    run?.status === "interrupted" ||
    run?.status === "created";

  async function handleResume() {
    if (!runId || !run) {
      return;
    }

    setActionFeedback(null);
    try {
      await resumeMutation.mutateAsync({
        runId,
        agentId: run.agentId,
      });
      setActionFeedback({
        tone: "success",
        message: "已提交恢复请求，运行会从最近一次 checkpoint 继续执行。",
      });
    } catch (error) {
      setActionFeedback({
        tone: "error",
        message: getControlErrorMessage(error),
      });
    }
  }

  async function handleInterrupt() {
    if (!runId || !run) {
      return;
    }

    setActionFeedback(null);
    try {
      await interruptMutation.mutateAsync({
        runId,
        agentId: run.agentId,
      });
      setActionFeedback({
        tone: "success",
        message: "已提交中断请求，当前运行会尽量停止并保留恢复点。",
      });
    } catch (error) {
      setActionFeedback({
        tone: "error",
        message: getControlErrorMessage(error),
      });
    }
  }

  async function handleCancel() {
    if (!runId || !run) {
      return;
    }

    const confirmed = window.confirm("取消后该运行将不可恢复，确认继续吗？");
    if (!confirmed) {
      return;
    }

    setActionFeedback(null);
    try {
      await cancelMutation.mutateAsync({
        runId,
        agentId: run.agentId,
      });
      setActionFeedback({
        tone: "success",
        message: "已提交取消请求，当前运行会停止且不再允许恢复。",
      });
    } catch (error) {
      setActionFeedback({
        tone: "error",
        message: getControlErrorMessage(error),
      });
    }
  }

  return (
    <section className="h-full overflow-y-auto pr-2 space-y-6 animate-fade-in">
      <div className="select-none">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          监控和剖析一次智能体流运行。查看底层输入输出数据、调用状态及各个工具执行的完整历史轨迹。
        </p>
      </div>

      {!runId ? <ErrorState message="缺少运行 ID，无法加载详情。" /> : null}

      {runId && runQuery.isLoading ? (
        <Card className="flex items-center justify-center p-8">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
            </span>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">正在加载运行详情...</p>
          </div>
        </Card>
      ) : null}

      {runId && runQuery.isError ? (
        <ErrorState message={runQuery.error.message} />
      ) : null}

      {runId && !runQuery.isLoading && !runQuery.isError && runQuery.data ? (
        <>
          <Card className="space-y-5 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between border-b border-slate-100 dark:border-slate-800/50 pb-4">
              <div className="min-w-0">
                <h2 className="truncate text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
                  运行 ID: <span className="font-mono text-xs">{runQuery.data.id}</span>
                </h2>
                <p className="mt-1 break-all text-xs font-mono text-slate-400 dark:text-slate-500">
                  关联会话 ID: {runQuery.data.conversationId ?? "尚未关联"}
                </p>
              </div>
              
              <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto shrink-0 select-none">
                <Badge variant={getBadgeVariant(runQuery.data.status)} className="uppercase text-[9px] tracking-wider px-3 py-1">
                  状态: {runQuery.data.status}
                </Badge>
                {canResume ? (
                  <Button size="sm" onClick={() => void handleResume()} disabled={isActionPending} className="text-xs px-3 py-1">
                    恢复运行
                  </Button>
                ) : null}
                {canInterrupt ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void handleInterrupt()}
                    disabled={isActionPending}
                    className="text-xs px-3 py-1"
                  >
                    中断运行
                  </Button>
                ) : null}
                {canCancel ? (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => void handleCancel()}
                    disabled={isActionPending}
                    className="text-xs px-3 py-1"
                  >
                    取消运行
                  </Button>
                ) : null}
              </div>
            </div>

            {actionFeedback ? (
              <div
                className={
                  actionFeedback.tone === "success"
                    ? "rounded-2xl border border-emerald-200 bg-emerald-50/50 dark:border-emerald-900/30 dark:bg-emerald-950/20 px-4 py-3 text-xs text-emerald-800 dark:text-emerald-400"
                    : "rounded-2xl border border-red-200 bg-red-50/50 dark:border-red-900/30 dark:bg-red-950/20 px-4 py-3 text-xs text-red-700 dark:text-red-400"
                }
              >
                {actionFeedback.message}
              </div>
            ) : null}

            <div className="grid gap-4 text-xs md:grid-cols-2 lg:grid-cols-5 pt-1">
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  路由 Agent
                </p>
                <p className="mt-1 break-all text-slate-700 dark:text-slate-350 font-mono">
                  {runQuery.data.agentId ?? "未知"}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  触发时间
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300">
                  {runQuery.data.startedAt ? formatDate(runQuery.data.startedAt) : "暂无"}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  更新时间
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300">
                  {runQuery.data.updatedAt ? formatDate(runQuery.data.updatedAt) : "暂无"}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  结束时间
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300">
                  {runQuery.data.finishedAt ? formatDate(runQuery.data.finishedAt) : <span className="text-brand-500 font-semibold animate-pulse">进行中</span>}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  执行时长
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300 font-mono">
                  {runQuery.data.durationMs !== null ? `${runQuery.data.durationMs} ms` : "---"}
                </p>
              </div>
            </div>

            <div className="grid gap-4 text-xs md:grid-cols-2 pt-2 border-t border-slate-100 dark:border-slate-800/40">
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  底层 Trace ID
                </p>
                <p className="mt-1 break-all text-slate-700 dark:text-slate-350 font-mono font-semibold">
                  {runQuery.data.traceId ?? "暂无数据"}
                </p>
              </div>
              <div>
                <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                  执行工具次数
                </p>
                <p className="mt-1 text-slate-700 dark:text-slate-300 font-bold">{runQuery.data.toolCalls.length} 次</p>
              </div>
            </div>

            {runQuery.data.errorMessage ? (
              <div className="rounded-2xl border border-red-200 bg-red-50/50 dark:border-red-950/20 dark:bg-red-950/15 px-4 py-3 text-xs text-red-700 dark:text-red-400 select-text">
                <span className="font-bold">异常原因:</span> {runQuery.data.errorMessage}
                {runQuery.data.errorCode ? ` [Code: ${runQuery.data.errorCode}]` : ""}
              </div>
            ) : null}

            {runQuery.data.interruptionReason ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50/50 dark:border-amber-950/20 dark:bg-amber-950/15 px-4 py-3 text-xs text-amber-800 dark:text-amber-400 select-text">
                <span className="font-bold">挂起原因:</span> {runQuery.data.interruptionReason}
              </div>
            ) : null}
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-4 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
              <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">输入参数 (Input)</h2>
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">归档的智能体运行初始输入。</p>
              </div>
              <ScrollArea className="max-h-[360px]">
                <pre className="whitespace-pre-wrap break-all rounded-2xl border border-slate-200 bg-slate-950/95 px-4 py-4 text-xs font-mono text-emerald-400 dark:border-slate-850 dark:bg-slate-950 shadow-inner select-text leading-5">
                  {renderJson(runQuery.data.input)}
                </pre>
              </ScrollArea>
            </Card>

            <Card className="space-y-4 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
              <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">输出结果 (Output)</h2>
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">归档的智能体运行最终输出。</p>
              </div>
              <ScrollArea className="max-h-[360px]">
                <pre className="whitespace-pre-wrap break-all rounded-2xl border border-slate-200 bg-slate-950/95 px-4 py-4 text-xs font-mono text-sky-400 dark:border-slate-850 dark:bg-slate-950 shadow-inner select-text leading-5">
                  {renderJson(runQuery.data.output)}
                </pre>
              </ScrollArea>
            </Card>
          </div>

          <Card className="space-y-4 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
            <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">工具轨迹监控 (Tool Call Stack)</h2>
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                运行中所有触发的第三方工具/子节点调用的执行轨迹与快照。
              </p>
            </div>

            {runQuery.data.toolCalls.length === 0 ? (
              <EmptyState
                title="暂无工具调用记录"
                description="本次运行流未涉及任何需要触发的工具或本地计算节点。"
              />
            ) : (
              <div className="grid gap-4">
                {runQuery.data.toolCalls.map((toolCall) => (
                  <Card
                    key={toolCall.id}
                    className="space-y-4 border border-slate-200/60 bg-slate-50/45 dark:border-slate-800/60 dark:bg-slate-950/30 shadow-none transition-all duration-300 hover:border-slate-300 dark:hover:border-slate-700/80 p-5"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between border-b border-slate-200/40 dark:border-slate-800/40 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-mono">
                          {toolCall.toolName}
                        </h3>
                        <p className="mt-1 text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                          调用 ID: {toolCall.id}
                        </p>
                        <p className="mt-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                          执行 Agent: {toolCall.agentId ?? runQuery.data!.agentId ?? "未知"}
                        </p>
                      </div>
                      <Badge variant={toolCall.status === "success" || toolCall.status === "completed" ? "success" : toolCall.status === "failed" ? "destructive" : "default"} className="self-start lg:self-auto shrink-0 font-bold text-[9px] uppercase tracking-wider">
                        {toolCall.status}
                      </Badge>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                      <div>
                        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 select-none">
                          工具入参 (Input)
                        </p>
                        <pre className="whitespace-pre-wrap break-all rounded-2xl border border-slate-200/60 bg-slate-950/90 px-4 py-3 text-xs font-mono text-amber-500/90 dark:border-slate-800/80 dark:bg-slate-950 shadow-inner select-text leading-5">
                          {renderJson(toolCall.input)}
                        </pre>
                      </div>
                      <div>
                        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 select-none">
                          工具出参 (Output)
                        </p>
                        <pre className="whitespace-pre-wrap break-all rounded-2xl border border-slate-200/60 bg-slate-950/90 px-4 py-3 text-xs font-mono text-indigo-400 dark:border-slate-800/80 dark:bg-slate-950 shadow-inner select-text leading-5">
                          {renderJson(toolCall.output)}
                        </pre>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </Card>
        </>
      ) : null}
    </section>
  );
}
