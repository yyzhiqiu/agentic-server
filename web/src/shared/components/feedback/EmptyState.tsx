type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-sm text-slate-600">
      <p className="font-medium text-slate-900">{title}</p>
      <p className="mt-2">{description}</p>
    </div>
  );
}
