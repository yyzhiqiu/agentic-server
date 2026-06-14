import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type SharedProps = {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg" | "icon";
};

type ButtonLikeProps = SharedProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: false;
  };

type LinkLikeProps = SharedProps &
  AnchorHTMLAttributes<HTMLAnchorElement> & {
    asChild: true;
  };

function getButtonClassName(
  variant: SharedProps["variant"] = "primary",
  size: SharedProps["size"] = "md",
  className?: string,
) {
  return cn(
    "inline-flex items-center justify-center rounded-full font-medium transition-all duration-200 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:pointer-events-none disabled:opacity-50 select-none",
    variant === "primary" && "bg-brand-700 text-white shadow-sm hover:bg-brand-850 dark:bg-brand-600 dark:hover:bg-brand-500",
    variant === "secondary" && "bg-white text-slate-800 border border-slate-200 hover:bg-slate-50 hover:text-slate-900 dark:bg-slate-800/80 dark:text-slate-200 dark:border-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-100",
    variant === "ghost" && "text-slate-700 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/70 dark:hover:text-slate-100",
    variant === "destructive" && "bg-red-650 text-white hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-650",
    size === "sm" && "px-3 py-1.5 text-xs",
    size === "md" && "px-4 py-2 text-sm",
    size === "lg" && "px-6 py-2.5 text-base",
    size === "icon" && "p-2",
    className,
  );
}

export function Button(props: ButtonLikeProps | LinkLikeProps) {
  if (props.asChild) {
    const {
      children,
      className,
      variant,
      size,
      asChild,
      ...rest
    } = props;
    void asChild;

    return (
      <a
        className={getButtonClassName(variant, size, className)}
        {...rest}
      >
        {children}
      </a>
    );
  }

  const { children, className, variant, size, ...rest } = props;

  return (
    <button
      className={getButtonClassName(variant, size, className)}
      {...rest}
    >
      {children}
    </button>
  );
}
