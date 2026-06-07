type LoadingStateProps = {
  title?: string;
};

export function LoadingState({
  title = "正在加载数据...",
}: LoadingStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-500">
      {title}
    </div>
  );
}
