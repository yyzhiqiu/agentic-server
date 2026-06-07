import { cn } from "@/shared/lib/cn";

type MessageBubbleProps = {
  role: string;
  content: string;
};

export function MessageBubble({ role, content }: MessageBubbleProps) {
  return (
    <div
      className={cn(
        "max-w-3xl rounded-2xl px-4 py-3 text-sm shadow-sm",
        role === "user"
          ? "ml-auto bg-brand-700 text-white"
          : "bg-white/90 text-slate-800",
      )}
    >
      <p className="mb-1 text-xs uppercase tracking-[0.2em] opacity-70">{role}</p>
      <p className="leading-6">{content}</p>
    </div>
  );
}
