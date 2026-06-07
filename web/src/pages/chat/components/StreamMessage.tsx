type StreamMessageProps = {
  content: string;
  active?: boolean;
};

export function StreamMessage({
  content,
  active = false,
}: StreamMessageProps) {
  return (
    <div className="rounded-2xl border border-dashed border-brand-500/40 bg-brand-50/70 px-4 py-3 text-sm text-brand-900">
      {active ? content : `流式状态：${content}`}
    </div>
  );
}
