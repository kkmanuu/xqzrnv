import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type FcPoint, type Mode, type Publication } from "../api";
import { mw, ukClock, ukFull, ukTime } from "../format";
import { Empty, ErrorBox, Loading } from "../ui";

export default function Inspector({ date, cutoff }: { date: string; cutoff: string }) {
  const [pubs, setPubs] = useState<Publication[] | null>(null);
  const [cutUtc, setCutUtc] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const [series, setSeries] = useState<Record<string, FcPoint[]>>({});
  const [actual, setActual] = useState<Record<string, number>>({});
  const [err, setErr] = useState("");

  useEffect(() => {
    setPubs(null); setErr(""); setSel(null);
    Promise.all([api.publications(date, cutoff), api.forecasts(date, cutoff, "asof"), api.forecasts(date, cutoff, "latest"), api.actuals(date, date)])
      .then(([p, asof, latest, act]) => {
        setPubs(p.publications); setCutUtc(p.cutoff_utc);
        setSeries({ asof: asof.data, latest: latest.data });
        setActual(Object.fromEntries(act.data.map((d) => [d.start_time, d.actual_mw])));
      })
      .catch((e) => setErr(e.message));
  }, [date, cutoff]);

  useEffect(() => {
    if (!sel) return;
    api.forecasts(date, cutoff, "asof" as Mode, sel).then((r) => setSeries((s) => ({ ...s, picked: r.data }))).catch((e) => setErr(e.message));
  }, [sel, date, cutoff]);

  const chart = useMemo(() => {
    const byT = new Map<string, Record<string, number | string>>();
    const put = (k: string, pts: FcPoint[] | undefined) => pts?.forEach((p) => {
      const row = byT.get(p.start_time) ?? { t: p.start_time }; row[k] = p.forecast_mw; byT.set(p.start_time, row);
    });
    put("asof", series.asof); put("latest", series.latest); if (sel) put("picked", series.picked);
    Object.entries(actual).forEach(([t, v]) => { const row = byT.get(t) ?? { t }; row.actual = v; byT.set(t, row); });
    return [...byT.values()].sort((a, b) => String(a.t).localeCompare(String(b.t)));
  }, [series, actual, sel]);

  if (err) return <ErrorBox message={err} />;
  if (!pubs) return <Loading what="publications" />;
  if (!pubs.length) return <Empty>No forecast publications cover {date}.</Empty>;

  return (
    <div className="row g-3">
      <div className="col-lg-4">
        <div className="panel">
          <h2>Publications for {date}</h2>
          <p className="hint">Decision cutoff: <strong>{ukFull(cutUtc)}</strong>. Forecasts published after it were not available to the trader.</p>
          <div style={{ maxHeight: 520, overflow: "auto" }}>
            {pubs.map((p) => (
              <button key={p.publish_time} className={`pub ${sel === p.publish_time ? "sel" : ""} ${p.available_at_cutoff ? "" : "late"}`} onClick={() => setSel(p.publish_time)}>
                <span>{ukTime(p.publish_time)}</span>
                {p.is_latest_before_cutoff && <span className="tag cut">used for decision</span>}
                {p.is_latest_overall && <span className="tag now">latest now</span>}
                {!p.available_at_cutoff && <span className="tag">after cutoff</span>}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="col-lg-8">
        <div className="panel">
          <h2>Day-ahead view of {date}</h2>
          <p className="hint">Green-tagged publication vs the latest forecast vs what actually happened. Times are UK local ({ukClock(cutUtc)} cutoff).</p>
          <div style={{ height: 380 }}>
            <ResponsiveContainer>
              <LineChart data={chart}>
                <CartesianGrid stroke="#e4eaea" />
                <XAxis dataKey="t" tickFormatter={(t) => ukClock(t)} minTickGap={40} fontSize={12} />
                <YAxis unit=" MW" width={80} fontSize={12} />
                <Tooltip labelFormatter={(t) => ukFull(String(t))} formatter={(v: number) => mw(v)} />
                <Legend />
                <Line dataKey="asof" name="Used for decision" stroke="var(--forecast)" dot={false} strokeWidth={2} connectNulls isAnimationActive={false} />
                <Line dataKey="latest" name="Latest available now" stroke="#7a5ea8" dot={false} strokeDasharray="5 4" connectNulls isAnimationActive={false} />
                {sel && <Line dataKey="picked" name="Selected publication" stroke="#444" dot={false} connectNulls isAnimationActive={false} />}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
