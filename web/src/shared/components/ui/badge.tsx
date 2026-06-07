import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export function Badge({
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-900",
        className,
      )}
      {...props}
    />
  );
}
