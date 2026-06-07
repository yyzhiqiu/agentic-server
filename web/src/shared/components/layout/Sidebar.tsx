import { Bot, Files, History, MessageSquare, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

import { APP_NAME } from "@/shared/constants/app";
import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

const navItems = [
  { to: ROUTES.chat, label: "Chat", icon: MessageSquare },
  { to: ROUTES.conversations, label: "Conversations", icon: History },
  { to: ROUTES.agentRuns, label: "Agent Runs", icon: Bot },
  { to: ROUTES.files, label: "Files", icon: Files },
  { to: ROUTES.settings, label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 rounded-3xl bg-brand-900 p-5 text-white shadow-[0_20px_60px_rgba(40,53,15,0.24)] lg:block">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.3em] text-brand-100/70">
          Workspace
        </p>
        <h1 className="mt-2 text-2xl font-semibold">{APP_NAME}</h1>
        <p className="mt-3 text-sm text-brand-100/80">
          A shared workspace for chat, conversations, run history, files, and
          configuration.
        </p>
      </div>

      <nav className="space-y-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition-colors",
                isActive
                  ? "bg-white text-brand-900"
                  : "text-brand-100/90 hover:bg-white/10",
              )
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
