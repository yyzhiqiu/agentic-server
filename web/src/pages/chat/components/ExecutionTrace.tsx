import {
  Bot,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  LoaderCircle,
  Network,
  Wrench,
} from "lucide-react";

import type {
  AgentExecutionActivity,
  ExecutionActivity,
  NodeExecutionActivity,
  ToolExecutionActivity,
} from "@/pages/chat/chatTimeline";
import { Badge } from "@/shared/components/ui/badge";

type ExecutionTraceProps = {
  activities: ExecutionActivity[];
};

const AGENT_LABELS: Record<string, string> = {
  coordinator_agent: "智能体协调器",
  chat_agent: "通用对话智能体",
  route_planner_agent: "出行规划智能体",
};

const TOOL_LABELS: Record<string, string> = {
  get_time: "获取当前时间",
  search_tool: "搜索信息",
  calculator_tool: "执行计算",
  maps_direction_driving: "规划驾车路线",
  maps_direction_walking: "规划步行路线",
  maps_direction_transit_integrated: "规划公交路线",
  maps_geo: "解析地点",
  maps_text_search: "搜索地点",
};

const NODE_LABELS: Record<string, string> = {
  route_decision: "识别意图并选择智能体",
  general_chat: "生成通用回复",
  model: "生成回复",
  tools: "执行工具",
  route_prepare_branch: "校验路线参数",
  route_execute: "查询路线",
  route_finalize: "整理路线结果",
  human_interaction: "等待补充信息",
  route_resume_merge: "合并补充信息",
};

const INPUT_LABELS: Record<string, string> = {
  city: "城市",
  destination: "终点",
  destination_text: "终点",
  expression: "表达式",
  mode: "方式",
  origin: "起点",
  origin_text: "起点",
  query: "查询",
};

function renderJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}

function getAgentLabel(agentId: string) {
  return AGENT_LABELS[agentId] ?? agentId;
}

function getToolLabel(toolName: string) {
  return TOOL_LABELS[toolName] ?? toolName.replace(/_/g, " ");
}

function getNodeLabel(nodeName: string) {
  return NODE_LABELS[nodeName] ?? nodeName.replace(/_/g, " ");
}

function isSuccessfulStatus(status: string) {
  return status === "success" || status === "completed";
}

function isFailedStatus(status: string) {
  return status === "failed" || status === "error";
}

function isInterruptedStatus(status: string) {
  return status === "interrupted";
}

function isCancelledStatus(status: string) {
  return status === "cancelled";
}

function getStatusLabel(status: string) {
  if (status === "created") {
    return "准备中";
  }
  if (status === "running") {
    return "运行中";
  }
  if (isSuccessfulStatus(status)) {
    return "已完成";
  }
  if (isFailedStatus(status)) {
    return "失败";
  }
  if (isInterruptedStatus(status)) {
    return "等待继续";
  }
  if (isCancelledStatus(status)) {
    return "已取消";
  }
  return status;
}

function formatSummaryValue(value: unknown) {
  if (typeof value === "string") {
    return value.length > 42 ? `${value.slice(0, 42)}…` : value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length} 项`;
  }
  return null;
}

function summarizeInput(input: Record<string, unknown>) {
  const parts = Object.entries(input)
    .map(([key, value]) => {
      const formattedValue = formatSummaryValue(value);
      return formattedValue
        ? `${INPUT_LABELS[key] ?? key}：${formattedValue}`
        : null;
    })
    .filter((part): part is string => Boolean(part))
    .slice(0, 2);

  return parts.join(" · ") || "无参数";
}

function summarizeOutput(output: Record<string, unknown>) {
  const directValue =
    formatSummaryValue(output.value) ??
    formatSummaryValue(output.content) ??
    formatSummaryValue(output.message) ??
    formatSummaryValue(output.error);
  if (directValue) {
    return directValue;
  }

  for (const key of ["paths", "results", "hits", "items"]) {
    const value = output[key];
    if (Array.isArray(value)) {
      return `返回 ${value.length} 项结果`;
    }
  }

  return Object.keys(output).length > 0 ? "已返回结构化结果" : null;
}

function buildSummary(activities: ExecutionActivity[]) {
  const agentActivity = activities.find((activity) => activity.kind === "agent");
  const toolCount = activities.filter((activity) => activity.kind === "tool").length;
  const runningActivity = [...activities]
    .reverse()
    .find((activity) => activity.status === "running");

  if (runningActivity?.kind === "tool") {
    return `正在${getToolLabel(runningActivity.toolName)}`;
  }
  if (runningActivity?.kind === "node") {
    return `正在${getNodeLabel(runningActivity.nodeName)}`;
  }
  if (runningActivity?.kind === "agent") {
    return `正在路由至${getAgentLabel(runningActivity.targetAgentId)}`;
  }

  const parts: string[] = [];
  if (agentActivity?.kind === "agent") {
    parts.push(getAgentLabel(agentActivity.targetAgentId));
  }
  if (toolCount > 0) {
    parts.push(`${toolCount} 次工具调用`);
  }
  return parts.join(" · ") || "执行过程";
}

function ActivityStatusIcon({ status }: { status: string }) {
  if (status === "running" || status === "created") {
    return <LoaderCircle className="h-3.5 w-3.5 animate-spin text-brand-500" />;
  }
  if (isFailedStatus(status)) {
    return <CircleAlert className="h-3.5 w-3.5 text-rose-500" />;
  }
  if (isInterruptedStatus(status)) {
    return <CircleAlert className="h-3.5 w-3.5 text-amber-500" />;
  }
  if (isCancelledStatus(status)) {
    return <CircleAlert className="h-3.5 w-3.5 text-slate-400" />;
  }
  return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />;
}

function AgentActivityItem({
  activity,
}: {
  activity: AgentExecutionActivity;
}) {
  const switched =
    activity.sourceAgentId &&
    activity.sourceAgentId !== activity.targetAgentId;
  const routeDecision =
    activity.details.route_decision &&
    typeof activity.details.route_decision === "object" &&
    !Array.isArray(activity.details.route_decision)
      ? (activity.details.route_decision as Record<string, unknown>)
      : activity.details;
  const confidence =
    typeof routeDecision.confidence === "number"
      ? `${Math.round(routeDecision.confidence * 100)}%`
      : null;

  return (
    <div className="relative flex gap-3 pb-4">
      <div className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-violet-200 bg-violet-50 dark:border-violet-800 dark:bg-violet-950">
        <Bot className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="text-xs font-semibold text-slate-800 dark:text-slate-100">
            {switched ? "智能体路由" : "智能体执行"}
          </p>
          <span className="text-[11px] text-slate-500 dark:text-slate-400">
            {getAgentLabel(activity.targetAgentId)}
          </span>
          {confidence ? (
            <Badge variant="secondary" className="px-1.5 py-0 text-[9px]">
              置信度 {confidence}
            </Badge>
          ) : null}
        </div>
        {activity.reason ? (
          <p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">
            {activity.reason}
          </p>
        ) : null}
        <details className="group/route mt-1.5">
          <summary className="flex w-fit cursor-pointer list-none items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
            技术详情
            <ChevronDown className="h-3 w-3 transition-transform group-open/route:rotate-180" />
          </summary>
          <div className="mt-2 rounded-lg border border-slate-200/80 bg-white/80 p-2.5 dark:border-slate-800 dark:bg-slate-950/50">
            <p className="break-all font-mono text-[10px] text-slate-500 dark:text-slate-400">
              {activity.sourceAgentId
                ? `${activity.sourceAgentId} → ${activity.targetAgentId}`
                : activity.targetAgentId}
            </p>
            {Object.keys(activity.details).length > 0 ? (
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-md bg-slate-950 p-2 text-[10px] leading-4 text-slate-300">
                {renderJson(activity.details)}
              </pre>
            ) : null}
          </div>
        </details>
      </div>
    </div>
  );
}

function ToolActivityItem({ activity }: { activity: ToolExecutionActivity }) {
  const outputSummary = summarizeOutput(activity.output);

  return (
    <div className="relative flex gap-3 pb-4 last:pb-0">
      <div className="relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-sky-200 bg-sky-50 dark:border-sky-800 dark:bg-sky-950">
        <Wrench className="h-3.5 w-3.5 text-sky-600 dark:text-sky-400" />
      </div>
      <details className="group/tool min-w-0 flex-1 rounded-lg border border-slate-200/80 bg-white/70 dark:border-slate-800 dark:bg-slate-900/40">
        <summary className="flex cursor-pointer list-none items-start gap-2 p-2.5">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <p className="text-xs font-semibold text-slate-800 dark:text-slate-100">
                {getToolLabel(activity.toolName)}
              </p>
              <Badge
                variant={
                  isSuccessfulStatus(activity.status)
                    ? "success"
                    : isFailedStatus(activity.status)
                      ? "destructive"
                      : "warning"
                }
                className="px-1.5 py-0 text-[9px]"
              >
                {getStatusLabel(activity.status)}
              </Badge>
            </div>
            <p className="mt-1 truncate text-[11px] text-slate-500 dark:text-slate-400">
              {activity.status === "running"
                ? summarizeInput(activity.input)
                : outputSummary ?? summarizeInput(activity.input)}
            </p>
          </div>
          <ChevronDown className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform group-open/tool:rotate-180" />
        </summary>

        <div className="grid gap-2 border-t border-slate-200/70 p-2.5 dark:border-slate-800 md:grid-cols-2">
          <div className="min-w-0">
            <p className="mb-1.5 text-[10px] font-medium text-slate-500">
              调用参数
            </p>
            <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-all rounded-md bg-slate-950 p-2 text-[10px] leading-4 text-amber-300">
              {renderJson(activity.input)}
            </pre>
          </div>
          <div className="min-w-0">
            <p className="mb-1.5 text-[10px] font-medium text-slate-500">
              返回结果
            </p>
            <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-all rounded-md bg-slate-950 p-2 text-[10px] leading-4 text-slate-300">
              {activity.status === "running"
                ? "等待工具返回…"
                : renderJson(activity.output)}
            </pre>
          </div>
          {Object.keys(activity.metadata).length > 0 ? (
            <details className="group/meta md:col-span-2">
              <summary className="flex w-fit cursor-pointer list-none items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                元数据
                <ChevronDown className="h-3 w-3 transition-transform group-open/meta:rotate-180" />
              </summary>
              <pre className="mt-1.5 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-md bg-slate-950 p-2 text-[10px] leading-4 text-slate-300">
                {renderJson(activity.metadata)}
              </pre>
            </details>
          ) : null}
          <p className="break-all font-mono text-[9px] text-slate-400 md:col-span-2">
            {activity.toolName}
          </p>
        </div>
      </details>
    </div>
  );
}

function NodeActivityList({
  activities,
}: {
  activities: NodeExecutionActivity[];
}) {
  if (activities.length === 0) {
    return null;
  }

  return (
    <details className="group/nodes border-t border-slate-200/70 pt-2.5 dark:border-slate-800">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-[11px] text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200">
        <Network className="h-3.5 w-3.5" />
        <span className="flex-1">底层执行节点</span>
        <span className="text-[10px] text-slate-400">
          {activities.length} 个
        </span>
        <ChevronDown className="h-3.5 w-3.5 transition-transform group-open/nodes:rotate-180" />
      </summary>
      <div className="mt-2 space-y-1 rounded-lg bg-slate-100/70 p-2 dark:bg-slate-900/60">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center gap-2 rounded-md px-1.5 py-1"
          >
            <ActivityStatusIcon status={activity.status} />
            <span className="min-w-0 flex-1 truncate text-[11px] text-slate-600 dark:text-slate-300">
              {getNodeLabel(activity.nodeName)}
            </span>
            <span className="font-mono text-[9px] text-slate-400">
              {activity.nodeName}
            </span>
          </div>
        ))}
      </div>
    </details>
  );
}

export function ExecutionTrace({ activities }: ExecutionTraceProps) {
  if (activities.length === 0) {
    return null;
  }

  const agentActivities = activities.filter(
    (activity): activity is AgentExecutionActivity => activity.kind === "agent",
  );
  const toolActivities = activities.filter(
    (activity): activity is ToolExecutionActivity => activity.kind === "tool",
  );
  const nodeActivities = activities.filter(
    (activity): activity is NodeExecutionActivity => activity.kind === "node",
  );
  const traceStatus = activities.some(
    (activity) => activity.status === "running" || activity.status === "created",
  )
    ? "running"
    : activities.some((activity) => isFailedStatus(activity.status))
      ? "failed"
      : activities.some((activity) => isInterruptedStatus(activity.status))
        ? "interrupted"
        : activities.some((activity) => isCancelledStatus(activity.status))
          ? "cancelled"
          : "completed";

  return (
    <details className="group mb-3 overflow-hidden rounded-xl border border-slate-200/80 bg-slate-50/70 dark:border-slate-700/70 dark:bg-slate-950/35">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs text-slate-600 transition-colors hover:bg-slate-100/80 dark:text-slate-300 dark:hover:bg-slate-900/70">
        <ActivityStatusIcon status={traceStatus} />
        <span className="min-w-0 flex-1 truncate font-medium">
          {buildSummary(activities)}
        </span>
        <span className="text-[10px] text-slate-400">
          {getStatusLabel(traceStatus)}
        </span>
        <ChevronDown className="h-3.5 w-3.5 text-slate-400 transition-transform group-open:rotate-180" />
      </summary>

      <div className="border-t border-slate-200/70 px-3 py-3 dark:border-slate-800">
        {agentActivities.length > 0 || toolActivities.length > 0 ? (
          <div className="relative">
            <div className="absolute bottom-3 left-[11px] top-3 w-px bg-slate-200 dark:bg-slate-800" />
            {agentActivities.map((activity) => (
              <AgentActivityItem key={activity.id} activity={activity} />
            ))}
            {toolActivities.map((activity) => (
              <ToolActivityItem key={activity.id} activity={activity} />
            ))}
          </div>
        ) : null}
        <NodeActivityList activities={nodeActivities} />
      </div>
    </details>
  );
}
