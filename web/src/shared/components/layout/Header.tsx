import { useSearchParams, useLocation } from "react-router-dom";
import { Moon, Sun } from "lucide-react";

import { useConversationDetail } from "@/features/conversations/hooks";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { useTheme } from "@/shared/lib/ThemeContext";

function getPageTitle(pathname: string): string {
  if (pathname === "/chat" || pathname === "/") {
    return "智能体对话";
  }
  if (pathname.startsWith("/conversations")) {
    return "会话历史";
  }
  if (pathname.startsWith("/agent-runs")) {
    return "运行记录";
  }
  if (pathname.startsWith("/files")) {
    return "文件管理";
  }
  if (pathname.startsWith("/settings")) {
    return "系统设置";
  }
  return "多智能体控制台";
}

export function Header() {
  const { theme, toggleTheme } = useTheme();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const conversationId = searchParams.get("conversationId");
  const conversationQuery = useConversationDetail(conversationId ?? "");

  const isChatPage = location.pathname === "/chat" || location.pathname === "/";
  const activeAgentId = conversationQuery.data?.latestRun?.agentId 
    ?? conversationQuery.data?.agentId 
    ?? "coordinator_agent";

  return (
    <header className="rounded-2xl border border-slate-200/40 bg-white/45 px-5 py-2.5 shadow-sm backdrop-blur-md transition-colors duration-300 dark:border-slate-850 dark:bg-[#1e1e1f]/40 shrink-0">
      <div className="flex items-center justify-between">
        {/* 左侧放置精美的状态微标 */}
        <div className="flex items-center gap-3 select-none">
          <Badge variant="secondary" className="text-[10px] bg-slate-200/50 text-slate-700 dark:bg-slate-800/60 dark:text-slate-350 font-semibold px-2.5 py-0.5">
            {getPageTitle(location.pathname)}
          </Badge>
          {isChatPage && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-500"></span>
              </span>
              <span>当前运行：</span>
              <span className="font-mono font-bold bg-slate-200/45 dark:bg-slate-800/80 px-1.5 py-0.5 rounded text-[10px] text-slate-650 dark:text-slate-300">
                {activeAgentId}
              </span>
            </div>
          )}
        </div>
        
        {/* 右侧保留主题切换按钮 */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="w-8 h-8 rounded-full text-slate-600 hover:text-slate-950 dark:text-slate-300 dark:hover:text-slate-100 bg-transparent hover:bg-slate-200/50 dark:hover:bg-slate-800/60 transition-all duration-200"
            title={theme === "dark" ? "切换至浅色模式" : "切换至深色模式"}
          >
            {theme === "dark" ? (
              <Sun size={16} className="text-amber-400" />
            ) : (
              <Moon size={16} className="text-slate-600" />
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
