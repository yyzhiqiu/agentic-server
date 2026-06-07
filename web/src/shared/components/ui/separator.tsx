import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export function Separator({
  className,
  ...props
}: HTMLAttributes<HTMLHRElement>) {
  return <hr className={cn("border-slate-200", className)} {...props} />;
}
