import { Bot, User } from "lucide-react";

import { cn } from "@/shared/lib/cn";
import { Markdown } from "@/shared/components/ui/Markdown";

type MessageBubbleProps = {
  role: string;
  content: string;
  pending?: boolean;
};

export function MessageBubble({
  role,
  content,
  pending = false,
}: MessageBubbleProps) {
  const isUser = role === "user" || role === "resume";

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

