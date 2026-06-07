import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none ring-0 transition-colors placeholder:text-slate-400 focus:border-brand-500",
          className,
        )}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";
