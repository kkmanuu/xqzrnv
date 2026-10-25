import { useState } from "react";
import type { Analysis } from "../api";
import { mw } from "../format";

export default function Scenario({ a }: { a: Analysis }) {
  const [demand, setDemand] = useState(30000);
  const [other, setOther] = useState(12000);
  const m = a.metrics;
  const hasData = m.n > 0 && a.rows.length > 0;
  const wind = hasData ? a.rows.reduce((s, r) => s + r.forecast_mw, 0) / a.rows.length : null;
  const base = wind == null ? null : demand - other - wind;
  return (
    <>
      <div className="panel mb-3">
        <h2>How wind forecasts feed the procurement decision</h2>
        <p className="mb-0">Extra power to buy = electricity demand − wind − all other supply (nuclear, imports, etc.). This pilot has no demand or other-supply data, so it cannot tell you the requirement. What it does give you is the wind input and how wrong that input has historically been. Wind forecast error on its own is not the amount to buy.</p>
      </div>
      <div className="panel scenario">
        <h2>Illustrative scenario <span className="tag now">hypothetical</span></h2>
        <p className="hint">The two inputs below are numbers you type in. They are not Elexon data. Only the wind forecast and error figures come from the analysis.</p>
        <div className="row g-3 mb-3">
          <div className="col-md-6"><label className="form-label" htmlFor="dem">Average demand to serve (MW) — your assumption</label>
            <input id="dem" type="number" min={0} className="form-control" value={demand} onChange={(e) => setDemand(Number(e.target.value))} /></div>
          <div className="col-md-6"><label className="form-label" htmlFor="oth">Other supply already secured (MW) — your assumption</label>
            <input id="oth" type="number" min={0} className="form-control" value={other} onChange={(e) => setOther(Number(e.target.value))} /></div>
        </div>
        {wind == null ? <p className="text-muted mb-0">No wind forecast data for the current selection.</p> : (
          <table className="table table-sm mb-2">
            <tbody>
              <tr><td>Mean wind forecast (from data)</td><td>{mw(wind)}</td></tr>
              <tr><td>Shortfall if wind arrives as forecast (hypothetical)</td><td><strong>{mw(base)}</strong></td></tr>
              <tr><td>…if wind under-delivers by the historical P90 over-forecast ({mw(m.p90_error_mw ?? null)})</td><td>{mw(base! + (m.p90_error_mw ?? 0))}</td></tr>
              <tr><td>…if wind over-delivers by the historical P10 error ({mw(m.p10_error_mw ?? null)})</td><td>{mw(base! + (m.p10_error_mw ?? 0))}</td></tr>
            </tbody>
          </table>
        )}
        <p className="hint mb-0">Error percentiles pool every half-hour in the selected range; a negative shortfall means surplus. Positive error = forecast above actual.</p>
      </div>
    </>
  );
}
