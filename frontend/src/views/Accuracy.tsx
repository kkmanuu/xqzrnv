import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Analysis } from "../api";
import { mw } from "../format";
import { Empty } from "../ui";

export default function Accuracy({ a }: { a: Analysis }) {
  if (!a.metrics.n) return <Empty>No matched periods to analyse.</Empty>;
  const chart = (title: string, hint: string, data: object[], key: string) => (
    <div className="panel mb-3">
      <h2>{title}</h2><p className="hint mb-2">{hint}</p>
      <div style={{ height: 260 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid stroke="#e4eaea" /><XAxis dataKey={key} fontSize={12} /><YAxis unit=" MW" width={80} fontSize={12} />
            <Tooltip formatter={(v: number) => mw(v, 1)} /><Legend />
            <Bar dataKey="mae_mw" name="MAE" fill="var(--forecast)" isAnimationActive={false} />
            <Bar dataKey="rmse_mw" name="RMSE" fill="#7fb3cc" isAnimationActive={false} />
            <Bar dataKey="bias_mw" name="Bias" fill="var(--actual)" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
  return (
    <>
      {chart("Error by hour of day (UK local)", "Shows when in the day the forecast is least reliable.", a.by_hour, "hour")}
      {chart("Error by delivery day", "Shows whether certain weather days were harder to forecast.", a.by_day, "date")}
    </>
  );
}
