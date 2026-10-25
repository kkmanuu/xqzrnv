import type { ReactNode } from "react";

export function Kpi({ label, value, tip, sub }: { label: string; value: string; tip: string; sub?: string }) {
  return (
    <div className="panel kpi h-100">
      <span className="l" title={tip} tabIndex={0} aria-label={`${label}: ${tip}`}>{label}</span>
      <div className="v">{value}</div>
      {sub && <div className="hint">{sub}</div>}
    </div>
  );
}

export function Loading({ what = "data" }: { what?: string }) {
  return <div className="panel text-center py-5" role="status"><div className="spinner-border spinner-border-sm me-2" />Loading {what}…</div>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="alert alert-danger d-flex justify-content-between align-items-center" role="alert">
      <span>{message}</span>
      {onRetry && <button className="btn btn-sm btn-outline-danger" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="panel text-center text-muted py-5">{children}</div>;
}
