import { Bot, User, Wrench, ChevronDown, Cpu } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { Markdown } from "@/shared/components/ui/Markdown";

type MessageBubbleProps = {
  role: string;
  content: string;
  pending?: boolean;
  metadata?: Record<string, unknown>;
  name?: string | null;
};

interface RouteDecision {
  intent?: string;
  reason?: string;
  confidence?: number;
  source?: string;
}

const TOOL_NAME_MAP: Record<string, string> = {
  maps_geo: "高德地理编码 (maps_geo)",
  maps_text_search: "高德地点检索 (maps_text_search)",
  maps_direction_driving: "高德驾车路线规划 (maps_direction_driving)",
  maps_direction_walking: "高德步行路线规划 (maps_direction_walking)",
  maps_direction_transit_integrated: "高德公交路线规划 (maps_direction_transit_integrated)",
  web_search: "网页搜索 (web_search)",
};

const AGENT_NAME_MAP: Record<string, string> = {
  coordinator_agent: "协调入口 (coordinator_agent)",
  chat_agent: "通用回复 (chat_agent)",
  route_planner_agent: "路线规划 (route_planner_agent)",
  code_agent: "代码助手 (code_agent)",
};

function getToolLabel(name: string | null | undefined): string {
  if (!name) return "未知工具";
  return TOOL_NAME_MAP[name] || name;
}

function getAgentName(id: string | null | undefined): string {
  if (!id) return "未知智能体";
  return AGENT_NAME_MAP[id] || id;
}

export function MessageBubble({
  role,
  content,
  pending = false,
  metadata,
  name,
}: MessageBubbleProps) {
  // 如果是工具调用消息，渲染为整洁的、可折叠的内联诊断块，而不是普通的聊天气泡
  if (role === "tool") {
    const status = metadata?.status;
    const isError = status === "error";
    
    // 尝试美化工具输出 JSON
    let displayContent = content;
    try {
      const parsed = JSON.parse(content);
      displayContent = JSON.stringify(parsed, null, 2);
    } catch {
      // 保持原样
    }

    return (
      <div className="w-full pl-11 pr-4 py-1.5 animate-slide-up select-none">
        <details className="group border border-slate-200/60 dark:border-slate-800/80 rounded-xl bg-slate-50/50 dark:bg-slate-900/30 px-3.5 py-2.5 text-xs transition-all duration-300">
          <summary className="flex items-center justify-between cursor-pointer font-medium list-none outline-none text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-350">
            <div className="flex items-center gap-2">
              <Wrench size={14} className={isError ? "text-red-500" : "text-emerald-500 animate-pulse"} />
              <span>
                调用工具：
                <span className="font-semibold text-slate-700 dark:text-slate-300 font-mono bg-slate-100 dark:bg-slate-800/80 px-1.5 py-0.5 rounded mr-1">
                  {getToolLabel(name || (metadata?.tool_name as string))}
                </span>
                {isError ? "发生错误" : "运行完毕"}
              </span>
            </div>
            <ChevronDown size={14} className="text-slate-400 group-open:rotate-180 transition-transform duration-200" />
          </summary>
          <div className="mt-2.5 pt-2 border-t border-slate-200/40 dark:border-slate-800/50 text-slate-650 dark:text-slate-400 font-mono text-[10.5px] leading-relaxed overflow-x-auto max-h-60 whitespace-pre scrollbar-thin">
            {displayContent}
          </div>
        </details>
      </div>
    );
  }

  const isUser = role === "user" || role === "resume";
  const routeDecision = metadata?.route_decision as RouteDecision | undefined;
  const hasRouteDecision = typeof routeDecision === "object" && routeDecision !== null;

  return (
    <div
      className={cn(
        "flex items-start gap-3 w-full animate-slide-up",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      {/* 角色图标 */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full text-xs shadow-sm border transition-colors duration-300",
          isUser
            ? "bg-brand-50 border-brand-200 text-brand-900 dark:bg-brand-950 dark:border-brand-800 dark:text-brand-300"
            : "bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950 dark:border-emerald-900 dark:text-emerald-300",
        )}
      >
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>

      {/* 气泡内容 */}
      <div
        className={cn(
          "max-w-[78%] rounded-2xl px-4 py-3 text-sm shadow-sm transition-all duration-300",
          isUser
            ? "bg-gradient-to-tr from-brand-700 to-brand-600 text-white rounded-tr-none dark:from-brand-650 dark:to-brand-550"
            : "bg-white border border-slate-200/70 text-slate-800 dark:bg-slate-900/60 dark:border-slate-800/80 dark:text-slate-100 rounded-tl-none",
        )}
      >
        <div className="flex items-center justify-between gap-6 mb-1 border-b border-black/5 dark:border-white/5 pb-1 select-none">
          <span className="text-[10px] font-bold tracking-widest opacity-60">
            {isUser ? "YOU" : "AGENT"}
          </span>
          {pending && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
            </span>
          )}
        </div>

        {/* 渲染智能体切换路由决策 */}
        {hasRouteDecision && (
          <div className="mb-3 border-b border-black/5 dark:border-white/5 pb-2.5">
            <details className="group border border-slate-200/70 dark:border-slate-850 rounded-lg bg-slate-50/40 dark:bg-slate-950/20 px-2.5 py-1.5 text-[11px] transition-all">
              <summary className="flex items-center justify-between cursor-pointer font-semibold list-none outline-none text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-350">
                <div className="flex items-center gap-1.5">
                  <Cpu size={12} className="text-blue-500 animate-pulse" />
                  <span>
                    智能体分发路由成功 (至：{getAgentName(metadata?.agent_id as string)})
                  </span>
                </div>
                <ChevronDown size={12} className="text-slate-400 group-open:rotate-180 transition-transform duration-200" />
              </summary>
              <div className="mt-1.5 pt-1.5 border-t border-slate-200/30 dark:border-slate-800/50 text-[10.5px] text-slate-500 dark:text-slate-400 font-mono space-y-1">
                <div><span className="font-semibold text-slate-400 dark:text-slate-500">分发意图:</span> {routeDecision.intent === "route_planning" ? "路线规划 (route_planning)" : "通用对话 (general_chat)"}</div>
                {routeDecision.reason && <div><span className="font-semibold text-slate-400 dark:text-slate-500">分发依据:</span> {routeDecision.reason}</div>}
                {routeDecision.confidence !== undefined && routeDecision.confidence !== null && <div><span className="font-semibold text-slate-400 dark:text-slate-500">置信分值:</span> {routeDecision.confidence}</div>}
                <div><span className="font-semibold text-slate-400 dark:text-slate-500">判定来源:</span> {routeDecision.source === "llm" ? "大语言模型智能决策" : "兜底静态分发规则"}</div>
              </div>
            </details>
          </div>
        )}

        {pending && content === "等待流式响应中..." ? (
          <div className="flex items-center gap-1.5 py-2 px-1">
            <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400 dark:bg-slate-500 [animation-delay:-0.3s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400 dark:bg-slate-500 [animation-delay:-0.15s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400 dark:bg-slate-500"></div>
          </div>
        ) : (
          <Markdown content={content} />
        )}
      </div>
    </div>
  );
}


