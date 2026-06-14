import { useState } from "react";
import { Bot, Files, History, MessageSquare, Settings, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Button } from "@/shared/components/ui/button";
import { APP_NAME } from "@/shared/constants/app";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";
import logoImg from "@/assets/logo.png";

const navItems = [
  { to: ROUTES.chat, label: "智能体对话", icon: MessageSquare },
  { to: ROUTES.conversations, label: "会话历史", icon: History },
  { to: ROUTES.agentRuns, label: "运行记录", icon: Bot },
  { to: ROUTES.files, label: "文件管理", icon: Files },
  { to: ROUTES.settings, label: "系统设置", icon: Settings },
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(() => localStorage.getItem("sidebar_collapsed") === "true");

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar_collapsed", String(next));
      return next;
    });
  };

  return (
    <aside className={cn(
      "hidden shrink-0 rounded-[24px] bg-[#e9eef6] text-slate-800 lg:block border border-slate-200/40 dark:border-slate-800/65 dark:bg-[#1e1e1f] dark:text-slate-200 transition-all duration-300 flex flex-col justify-between shadow-[0_4px_20px_0_rgba(0,0,0,0.02)]",
      isCollapsed ? "w-20 p-4" : "w-64 p-6"
    )}>
      <div>
        <div className={cn("mb-8 select-none flex", isCollapsed ? "justify-center" : "items-center justify-between")}>
          {isCollapsed ? (
            /* 折叠状态下的 Logo：悬浮显示展开图标，点击展开 */
            <button
              onClick={toggleCollapse}
              className="relative w-8 h-8 flex items-center justify-center cursor-pointer group rounded-lg hover:bg-slate-350/30 dark:hover:bg-slate-800/40 focus:outline-none transition-colors duration-200"
              title="展开菜单"
            >
              <img
                src={logoImg}
                alt="Logo"
                className="w-6 h-6 object-contain shrink-0 transition-all duration-200 group-hover:opacity-0"
              />
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200 text-slate-650 dark:text-slate-300">
                <PanelLeftOpen size={16} />
              </div>
            </button>
          ) : (
            /* 展开状态下的常规 Logo 与标题，以及收起按钮 */
            <>
              <div className="flex items-center gap-2.5">
                <img src={logoImg} alt="Logo" className="w-6 h-6 object-contain shrink-0" />
                <h1 className="text-lg font-bold tracking-tight font-display text-slate-900 dark:text-slate-100 leading-none">
                  {APP_NAME}
                </h1>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleCollapse}
                className="w-7 h-7 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 bg-transparent hover:bg-slate-350/20 dark:hover:bg-slate-800/40 shrink-0"
                title="收起菜单"
              >
                <PanelLeftClose size={16} />
              </Button>
            </>
          )}
        </div>

        <nav className={cn("space-y-1.5", isCollapsed ? "flex flex-col items-center" : "")}>
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              title={isCollapsed ? label : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-2xl text-sm font-medium transition-all duration-200",
                  isCollapsed ? "justify-center w-12 h-12 rounded-xl" : "px-4 py-3.5 w-full",
                  isActive
                    ? "bg-[#d3e3fd] text-[#041e49] font-bold shadow-[0_2px_8px_0_rgba(4,30,73,0.05)] dark:bg-brand-600 dark:text-white dark:shadow-none"
                    : "text-slate-700 hover:bg-slate-350/40 dark:text-slate-400 dark:hover:bg-slate-800/50 dark:hover:text-slate-200",
                )
              }
            >
              <Icon size={18} className="shrink-0" />
              {!isCollapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className={cn("mt-8 pt-4 border-t border-slate-300/60 dark:border-slate-800/80 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-500", isCollapsed ? "justify-center" : "")}>
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        {!isCollapsed && <span>控制台服务已就绪</span>}
      </div>
    </aside>
  );
}
