type ErrorStateProps = {
  message: string;
};

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-5 text-sm text-red-700">
      {message}
    </div>
  );
}
