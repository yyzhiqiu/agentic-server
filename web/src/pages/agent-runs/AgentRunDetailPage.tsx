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
import { LoadingState } from "@/shared/components/feedback/LoadingState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { ScrollArea } from "@/shared/components/ui/scroll-area";
import { Separator } from "@/shared/components/ui/separator";
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

  if (status === "cancelled") {
    return "bg-slate-300 text-slate-800";
  }

  if (status === "failed") {
    return "bg-red-100 text-red-800";
  }

  return "bg-slate-200 text-slate-700";
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
    <section className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">
          Agent Run Detail
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">运行详情</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          这里展示状态摘要、所属 Agent、输入输出和工具调用轨迹，便于排查一次运行的完整上下文。
        </p>
      </div>

      {!runId ? <ErrorState message="缺少运行 ID，无法加载详情。" /> : null}

      {runId && runQuery.isLoading ? (
        <LoadingState title="正在加载运行详情..." />
      ) : null}

      {runId && runQuery.isError ? (
        <ErrorState message={runQuery.error.message} />
      ) : null}

      {runId && !runQuery.isLoading && !runQuery.isError && runQuery.data ? (
        <>
          <Card className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <h2 className="truncate text-xl font-semibold text-slate-900">
                  运行 {runQuery.data.id}
                </h2>
                <p className="mt-2 break-all text-sm text-slate-500">
                  会话 ID: {runQuery.data.conversationId ?? "未关联"}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 lg:justify-end">
                <Badge className={getStatusTone(runQuery.data.status)}>
                  状态: {runQuery.data.status}
                </Badge>
                {canResume ? (
                  <Button size="sm" onClick={() => void handleResume()} disabled={isActionPending}>
                    恢复运行
                  </Button>
                ) : null}
                {canInterrupt ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void handleInterrupt()}
                    disabled={isActionPending}
                  >
                    中断运行
                  </Button>
                ) : null}
                {canCancel ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => void handleCancel()}
                    disabled={isActionPending}
                    className="border-red-200 text-red-700 hover:bg-red-50"
                  >
                    取消运行
                  </Button>
                ) : null}
              </div>
            </div>

            <Separator />

            {actionFeedback ? (
              <div
                className={
                  actionFeedback.tone === "success"
                    ? "rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
                    : "rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
                }
              >
                {actionFeedback.message}
              </div>
            ) : null}

            <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-2 lg:grid-cols-5">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Agent
                </p>
                <p className="mt-1 break-all text-slate-700">
                  {runQuery.data.agentId ?? "未知"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  开始时间
                </p>
                <p className="mt-1 text-slate-700">
                  {runQuery.data.startedAt ? formatDate(runQuery.data.startedAt) : "暂无"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  更新时间
                </p>
                <p className="mt-1 text-slate-700">
                  {runQuery.data.updatedAt ? formatDate(runQuery.data.updatedAt) : "暂无"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  结束时间
                </p>
                <p className="mt-1 text-slate-700">
                  {runQuery.data.finishedAt ? formatDate(runQuery.data.finishedAt) : "运行中"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  耗时
                </p>
                <p className="mt-1 text-slate-700">
                  {runQuery.data.durationMs !== null ? `${runQuery.data.durationMs} ms` : "暂无"}
                </p>
              </div>
            </div>

            <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  Trace ID
                </p>
                <p className="mt-1 break-all text-slate-700">
                  {runQuery.data.traceId ?? "暂无"}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                  工具调用数量
                </p>
                <p className="mt-1 text-slate-700">{runQuery.data.toolCalls.length}</p>
              </div>
            </div>

            {runQuery.data.errorMessage ? (
              <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                失败原因: {runQuery.data.errorMessage}
                {runQuery.data.errorCode ? ` (${runQuery.data.errorCode})` : ""}
              </div>
            ) : null}

            {runQuery.data.interruptionReason ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                控制原因: {runQuery.data.interruptionReason}
              </div>
            ) : null}
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">输入</h2>
                <p className="mt-1 text-sm text-slate-500">这里展示持久化的运行输入。</p>
              </div>
              <ScrollArea className="max-h-[360px]">
                <pre className="whitespace-pre-wrap break-all rounded-2xl bg-slate-900 px-4 py-4 text-xs text-slate-100">
                  {renderJson(runQuery.data.input)}
                </pre>
              </ScrollArea>
            </Card>

            <Card className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">输出</h2>
                <p className="mt-1 text-sm text-slate-500">这里展示持久化的运行输出。</p>
              </div>
              <ScrollArea className="max-h-[360px]">
                <pre className="whitespace-pre-wrap break-all rounded-2xl bg-slate-900 px-4 py-4 text-xs text-slate-100">
                  {renderJson(runQuery.data.output)}
                </pre>
              </ScrollArea>
            </Card>
          </div>

          <Card className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">工具调用</h2>
              <p className="mt-1 text-sm text-slate-500">
                这里展示后端已持久化的工具调用轨迹。
              </p>
            </div>

            {runQuery.data.toolCalls.length === 0 ? (
              <EmptyState
                title="没有工具调用记录"
                description="这次运行没有已持久化的工具调用记录。命中工具节点后，这里会展示对应轨迹。"
              />
            ) : (
              <div className="grid gap-4">
                {runQuery.data.toolCalls.map((toolCall) => (
                  <Card
                    key={toolCall.id}
                    className="space-y-4 border border-slate-200 bg-slate-50/70 shadow-none"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900">
                          {toolCall.toolName}
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                          工具调用 ID: {toolCall.id}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">
                          Agent: {toolCall.agentId ?? runQuery.data.agentId ?? "未知"}
                        </p>
                      </div>
                      <Badge>{toolCall.status}</Badge>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-400">
                          Input
                        </p>
                        <pre className="whitespace-pre-wrap break-all rounded-2xl bg-slate-900 px-4 py-4 text-xs text-slate-100">
                          {renderJson(toolCall.input)}
                        </pre>
                      </div>
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-400">
                          Output
                        </p>
                        <pre className="whitespace-pre-wrap break-all rounded-2xl bg-slate-900 px-4 py-4 text-xs text-slate-100">
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
