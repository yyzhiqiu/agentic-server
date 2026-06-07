import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-white/70 bg-white/80 p-5 shadow-[0_12px_40px_rgba(40,53,15,0.08)] backdrop-blur",
        className,
      )}
      {...props}
    />
  );
}
