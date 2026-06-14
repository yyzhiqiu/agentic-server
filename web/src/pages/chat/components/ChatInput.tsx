import type { FormEvent, KeyboardEvent } from "react";
import { Send } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { Textarea } from "@/shared/components/ui/textarea";

type ChatInputProps = {
  value: string;
  disabled?: boolean;
  isSubmitting?: boolean;
  submitLabel?: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatInput({
  value,
  disabled = false,
  isSubmitting = false,
  submitLabel = "发送",
  onChange,
  onSubmit,
}: ChatInputProps) {
  const canSubmit = value.trim().length > 0 && !disabled && !isSubmitting;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    onSubmit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    onSubmit();
  }

  return (
    <form
      className="space-y-3 rounded-2xl border border-slate-200/80 bg-white/50 p-4 shadow-sm transition-all duration-300 focus-within:shadow-md dark:border-slate-800/80 dark:bg-slate-900/40"
      onSubmit={handleSubmit}
    >
      <Textarea
        placeholder="输入您的问题，系统将为您匹配最佳智能体工作流..."
        rows={2}
        value={value}
        disabled={disabled || isSubmitting}
        onKeyDown={handleKeyDown}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        className="resize-none bg-transparent border-none p-0 focus:ring-0 dark:bg-transparent dark:focus:ring-0 text-sm leading-6"
      />
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-100 dark:border-slate-800/60">
        <p className="text-[11px] text-slate-400 dark:text-slate-500 select-none">
          按 Enter 发送，Shift + Enter 换行
        </p>
        <Button
          type="submit"
          disabled={!canSubmit}
          className="gap-2 px-4 py-1.5 shadow-sm"
        >
          <Send size={14} className={isSubmitting ? "animate-pulse" : ""} />
          <span>{isSubmitting ? "发送中..." : submitLabel}</span>
        </Button>
      </div>
    </form>
  );
}
