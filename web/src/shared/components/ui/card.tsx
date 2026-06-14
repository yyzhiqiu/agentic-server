import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-slate-200/80 bg-white/75 p-5 shadow-sm backdrop-blur-md transition-all duration-300 hover:shadow-md dark:border-slate-800/80 dark:bg-slate-900/60 dark:shadow-none dark:hover:border-slate-700/80",
        className,
      )}
      {...props}
    />
  );
}
