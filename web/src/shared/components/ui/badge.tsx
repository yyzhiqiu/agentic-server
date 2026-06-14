import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "warning" | "info" | "destructive" | "secondary";
};

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors duration-200",
        variant === "default" && "bg-brand-50 text-brand-900 dark:bg-brand-950/80 dark:text-brand-300",
        variant === "secondary" && "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200",
        variant === "success" && "bg-emerald-50 text-emerald-800 border border-emerald-200/50 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-800/40",
        variant === "warning" && "bg-amber-50 text-amber-800 border border-amber-200/50 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800/40",
        variant === "info" && "bg-sky-50 text-sky-800 border border-sky-200/50 dark:bg-sky-950/30 dark:text-sky-400 dark:border-sky-800/40",
        variant === "destructive" && "bg-red-50 text-red-800 border border-red-200/50 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800/40",
        className,
      )}
      {...props}
    />
  );
}
