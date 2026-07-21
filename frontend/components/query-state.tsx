export function LoadingState({ label = "Loading workspace data" }: { label?: string }) {
  return (
    <div className="state-panel" role="status">
      <span className="loading-pulse" aria-hidden="true" />
      <p>{label}…</p>
    </div>
  );
}

export function ErrorState({
  title = "Could not reach the ReAgent API",
  message,
}: {
  title?: string;
  message?: string;
}) {
  return (
    <div className="state-panel state-error" role="alert">
      <span className="state-symbol" aria-hidden="true">!</span>
      <div>
        <strong>{title}</strong>
        <p>{message ?? "Check that the FastAPI backend is running, then try again."}</p>
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="empty-panel">
      <span aria-hidden="true">○</span>
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}
