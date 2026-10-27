import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Analysis, Meta } from "../api";
import { mw, pct, ukFull, ukTime } from "../format";
import { Empty, Kpi } from "../ui";

export default function Overview({ a, meta }: { a: Analysis; meta: Meta }) {
  const m = a.metrics;
  if (!m.n) return <Empty>No matched forecast/actual periods for this selection. {a.warnings.join(" ")}</Empty>;
  const avgF = a.rows.reduce((s, r) => s + r.forecast_mw, 0) / a.rows.length;
  const data = a.rows.map((r) => ({ t: r.start_time, forecast: r.forecast_mw, actual: r.actual_mw, error: r.error_mw }));
  return (
    <>
      <div className="row g-3 mb-3">
        <div className="col-6 col-xl-3"><Kpi label="MAE" value={mw(m.mae_mw)} tip="Mean absolute error: average size of the miss, ignoring direction." sub={`${m.n} matched periods`} /></div>
        <div className="col-6 col-xl-3"><Kpi label="RMSE" value={mw(m.rmse_mw)} tip="Root mean squared error: like MAE but penalises large misses more." /></div>
        <div className="col-6 col-xl-3"><Kpi label="Bias" value={mw(m.bias_mw, 1)} tip="Mean of forecast minus actual. Positive = forecasts run high (wind over-promised)." sub={m.bias_mw! > 0 ? "forecast higher than actual" : "forecast lower than actual"} /></div>
        <div className="col-6 col-xl-3"><Kpi label="MAPE" value={pct(m.mape_pct)} tip={`Mean absolute percentage error, only for periods with actual ≥ ${m.mape_min_actual_mw} MW (near-zero actuals make it meaningless).`} sub={`${m.mape_n} of ${m.n} periods used`} /></div>
      </div>
      <div className="panel mb-3">
        <h2>Forecast vs actual wind generation</h2>
        <p className="hint mb-2">
          Forecast = {a.mode === "asof" ? `latest publication before ${a.cutoff_local} UK time on the day before delivery` : "latest publication available overall"}.
          Mean forecast over the selection: {mw(avgF)}. Data fetched {meta.fetched_at ? ukFull(meta.fetched_at) : "n/a"}.
        </p>
        <div style={{ height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={data}>
              <CartesianGrid stroke="#e4eaea" />
              <XAxis dataKey="t" tickFormatter={(t) => ukTime(t)} minTickGap={60} fontSize={12} />
              <YAxis unit=" MW" width={80} fontSize={12} />
              <Tooltip labelFormatter={(t) => ukFull(String(t))} formatter={(v: number) => mw(v)} />
              <Legend />
              <Line dataKey="forecast" name="Forecast" stroke="var(--forecast)" dot={false} strokeWidth={1.8} isAnimationActive={false} />
              <Line dataKey="actual" name="Actual (FUELHH)" stroke="var(--actual)" dot={false} strokeWidth={1.8} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Forecast error over time (forecast − actual)</h2>
        <p className="hint mb-2">Above zero: wind was over-forecast, so more power had to be bought elsewhere than planned.</p>
        <div style={{ height: 240 }}>
          <ResponsiveContainer>
            <BarChart data={data}>
              <CartesianGrid stroke="#e4eaea" />
              <XAxis dataKey="t" tickFormatter={(t) => ukTime(t)} minTickGap={60} fontSize={12} />
              <YAxis unit=" MW" width={80} fontSize={12} />
              <Tooltip labelFormatter={(t) => ukFull(String(t))} formatter={(v: number) => mw(v)} />
              <Bar dataKey="error" name="Error" fill="var(--pos)" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}
