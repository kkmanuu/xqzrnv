import { useMemo, useState } from "react";
import type { Analysis, Row } from "../api";
import { mw, ukFull } from "../format";
import { Empty } from "../ui";

type Key = keyof Row;
const PAGE = 50;

export default function DataTable({ a }: { a: Analysis }) {
  const [key, setKey] = useState<Key>("start_time");
  const [asc, setAsc] = useState(true);
  const [page, setPage] = useState(0);
  const rows = useMemo(() => [...a.rows].sort((x, y) => {
    const d = x[key] < y[key] ? -1 : x[key] > y[key] ? 1 : 0; return asc ? d : -d;
  }), [a.rows, key, asc]);
  if (!rows.length) return <Empty>No rows for this selection.</Empty>;
  const th = (k: Key, label: string) => (
    <th role="button" tabIndex={0} aria-sort={key === k ? (asc ? "ascending" : "descending") : "none"}
        onClick={() => { key === k ? setAsc(!asc) : (setKey(k), setAsc(true)); setPage(0); }}
        onKeyDown={(e) => e.key === "Enter" && (key === k ? setAsc(!asc) : (setKey(k), setAsc(true)))}>
      {label}{key === k ? (asc ? " ▲" : " ▼") : ""}
    </th>
  );
  const pages = Math.ceil(rows.length / PAGE);
  return (
    <div className="panel">
      <div className="table-responsive">
        <table className="table table-sm align-middle">
          <thead><tr>{th("start_time", "Delivery time")}{th("publish_time", "Forecast published")}{th("forecast_mw", "Forecast (MW)")}{th("actual_mw", "Actual (MW)")}{th("error_mw", "Error (MW)")}</tr></thead>
          <tbody>
            {rows.slice(page * PAGE, (page + 1) * PAGE).map((r) => (
              <tr key={r.start_time}>
                <td>{ukFull(r.start_time)}</td><td>{ukFull(r.publish_time)}</td>
                <td>{mw(r.forecast_mw, 0)}</td><td>{mw(r.actual_mw, 0)}</td>
                <td className={r.error_mw > 0 ? "err-pos" : "err-neg"}>{r.error_mw > 0 ? "+" : ""}{r.error_mw.toFixed(0)}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <div className="d-flex justify-content-between align-items-center">
        <span className="hint">{rows.length} rows · error = forecast − actual</span>
        <div className="btn-group btn-group-sm">
          <button className="btn btn-outline-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
          <button className="btn btn-outline-secondary" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next ({page + 1}/{pages})</button>
        </div>
      </div>
    </div>
  );
}
