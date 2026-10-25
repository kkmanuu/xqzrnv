const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {}

async function get<T>(path: string, params: Record<string, string | undefined> = {}): Promise<T> {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][]);
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}?${q}`);
  } catch {
    throw new ApiError("Cannot reach the backend. Check that it is running and VITE_API_BASE_URL is correct.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { const b = await res.json(); detail = typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail); } catch { /* ignore */ }
    throw new ApiError(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export type Mode = "asof" | "latest";
export interface Meta {
  window: { from: string; to: string }; default_cutoff_local: string; timezone: string; units: string;
  fetched_at: string | null; latest_forecast_publish_time: string | null; latest_actual_start_time: string | null;
  counts: { actuals: number; forecasts: number }; cutoff_presets: { label: string; value: string }[];
}
export interface Metrics {
  n: number; mae_mw: number | null; rmse_mw: number | null; bias_mw: number | null; mape_pct: number | null;
  mape_n: number; mape_min_actual_mw: number; p10_error_mw?: number; p90_error_mw?: number;
}
export interface Row { start_time: string; publish_time: string; forecast_mw: number; actual_mw: number; error_mw: number; horizon_h: number }
export interface Group { n: number; mae_mw: number; rmse_mw: number; bias_mw: number; hour?: number; date?: string }
export interface Analysis { metrics: Metrics; rows: Row[]; by_hour: Group[]; by_day: Group[]; warnings: string[]; cutoff_local: string; mode: Mode }
export interface Publication { publish_time: string; periods: number; available_at_cutoff: boolean; is_latest_before_cutoff: boolean; is_latest_overall: boolean }
export interface FcPoint { start_time: string; publish_time: string; forecast_mw: number }

export const api = {
  meta: () => get<Meta>("/api/meta"),
  analysis: (from: string, to: string, mode: Mode, cutoff: string) => get<Analysis>("/api/analysis", { from, to, mode, cutoff }),
  publications: (date: string, cutoff: string) =>
    get<{ cutoff_utc: string; publications: Publication[] }>("/api/forecast-publications", { date, cutoff }),
  forecasts: (date: string, cutoff: string, mode: Mode, publish_time?: string) =>
    get<{ data: FcPoint[] }>("/api/forecasts", { date, cutoff, mode, publish_time }),
  actuals: (from: string, to: string) => get<{ data: { start_time: string; actual_mw: number }[] }>("/api/actuals", { from, to }),
};
