import { forwardRef } from "react";
import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition-colors placeholder:text-slate-400 focus:border-brand-500",
        className,
      )}
      {...props}
    />
  );
});

Textarea.displayName = "Textarea";
