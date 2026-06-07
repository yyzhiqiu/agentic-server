import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type SharedProps = {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
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
    "inline-flex items-center justify-center rounded-full font-medium transition-colors",
    variant === "primary" && "bg-brand-700 text-white hover:bg-brand-900",
    variant === "secondary" && "bg-white text-slate-900 ring-1 ring-slate-200 hover:bg-slate-50",
    variant === "ghost" && "text-slate-700 hover:bg-slate-100",
    size === "sm" && "px-3 py-2 text-sm",
    size === "md" && "px-4 py-2 text-sm",
    size === "lg" && "px-5 py-3 text-base",
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
