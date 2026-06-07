import type { FormEvent } from "react";

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

  return (
    <form
      className="space-y-3 rounded-2xl border border-white/70 bg-white/70 p-4 shadow-sm"
      onSubmit={handleSubmit}
    >
      <Textarea
        placeholder="输入你的问题，发送后将在上方显示回复内容。"
        rows={4}
        value={value}
        disabled={disabled || isSubmitting}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
      <div className="flex justify-end">
        <Button type="submit" disabled={!canSubmit}>
          {isSubmitting ? "发送中..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
