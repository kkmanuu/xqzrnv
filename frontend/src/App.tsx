import { useCallback, useEffect, useState } from "react";
import { api, type Analysis, type Meta, type Mode } from "./api";
import { ukFull } from "./format";
import { ErrorBox, Loading } from "./ui";
import Accuracy from "./views/Accuracy";
import DataTable from "./views/DataTable";
import Inspector from "./views/Inspector";
import Overview from "./views/Overview";
import Scenario from "./views/Scenario";

const TABS = ["Overview", "Publication inspector", "Accuracy", "Data table", "Procurement scenario"] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [tab, setTab] = useState<Tab>("Overview");
  const [from, setFrom] = useState(""); const [to, setTo] = useState("");
  const [mode, setMode] = useState<Mode>("asof");
  const [cutoff, setCutoff] = useState("09:20");
  const [day, setDay] = useState("");
  const [a, setA] = useState<Analysis | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.meta().then((m) => { setMeta(m); setFrom(m.window.from); setTo(m.window.to); setDay(m.window.from.slice(0, 8) + "15"); setCutoff(m.default_cutoff_local); })
      .catch((e) => setErr(e.message));
  }, []);

  const load = useCallback(() => {
    if (!from || !to) return;
    setA(null); setErr("");
    api.analysis(from, to, mode, cutoff).then(setA).catch((e) => setErr(e.message));
  }, [from, to, mode, cutoff]);
  useEffect(load, [load]);

  return (
    <div className="shell">
      <nav className="side" aria-label="Sections">
        <h1>Wind forecast desk</h1><small>GB day-ahead procurement</small>
        <div className="nav flex-column mt-4 gap-1">
          {TABS.map((t) => <button key={t} className={`nav-link ${tab === t ? "active" : ""}`} aria-current={tab === t} onClick={() => setTab(t)}>{t}</button>)}
        </div>
        {meta && <p className="hint mt-4" style={{ color: "#9fb5bb" }}>Latest forecast published<br />{meta.latest_forecast_publish_time ? ukFull(meta.latest_forecast_publish_time) : "n/a"}<br /><br />Data: Elexon BMRS (WINDFOR, FUELHH). Units: MW.</p>}
      </nav>
      <main>
        <div className="filters">
          <div className="row g-2 align-items-end">
            <div className="col-6 col-md-2"><label className="form-label small mb-0" htmlFor="f">From</label>
              <input id="f" type="date" className="form-control form-control-sm" min={meta?.window.from} max={to} value={from} onChange={(e) => setFrom(e.target.value)} /></div>
            <div className="col-6 col-md-2"><label className="form-label small mb-0" htmlFor="t">To</label>
              <input id="t" type="date" className="form-control form-control-sm" min={from} max={meta?.window.to} value={to} onChange={(e) => setTo(e.target.value)} /></div>
            <div className="col-6 col-md-3"><label className="form-label small mb-0" htmlFor="c">Decision cutoff (UK time, day before)</label>
              <select id="c" className="form-select form-select-sm" value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
                {(meta?.cutoff_presets ?? []).map((p) => <option key={p.value} value={p.value}>{p.value} · {p.label}</option>)}
              </select></div>
            <div className="col-6 col-md-3"><label className="form-label small mb-0" htmlFor="m">Forecast basis</label>
              <select id="m" className="form-select form-select-sm" value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
                <option value="asof">Known at cutoff (what a trader could use)</option><option value="latest">Latest published (hindsight)</option>
              </select></div>
            {tab === "Publication inspector" && <div className="col-6 col-md-2"><label className="form-label small mb-0" htmlFor="d">Delivery day</label>
              <input id="d" type="date" className="form-control form-control-sm" min={meta?.window.from} max={meta?.window.to} value={day} onChange={(e) => setDay(e.target.value)} /></div>}
          </div>
        </div>
        {err && <ErrorBox message={err} onRetry={meta ? load : () => location.reload()} />}
        {!meta && !err && <Loading what="dashboard" />}
        {meta && tab === "Publication inspector" && day && <Inspector date={day} cutoff={cutoff} />}
        {meta && tab !== "Publication inspector" && !a && !err && <Loading what="analysis" />}
        {meta && a && a.warnings.length > 0 && tab !== "Publication inspector" && <div className="alert alert-warning py-2" role="status">{a.warnings.join(" ")}</div>}
        {meta && a && tab === "Overview" && <Overview a={a} meta={meta} />}
        {a && tab === "Accuracy" && <Accuracy a={a} />}
        {a && tab === "Data table" && <DataTable a={a} />}
        {a && tab === "Procurement scenario" && <Scenario a={a} />}
      </main>
    </div>
  );
}
