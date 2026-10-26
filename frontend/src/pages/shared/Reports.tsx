import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage, downloadCsv } from "../../api/client";

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

export default function Reports() {
  const [available, setAvailable] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const now = new Date();
  const [params, setParams] = useState({
    ...defaultRange(),
    month: String(now.getMonth() + 1),
    year: String(now.getFullYear()),
    department_id: "",
  });

  useEffect(() => {
    api.get("/reports").then((r) => {
      setAvailable(r.data.reports);
      if (r.data.reports.length) setSelected(r.data.reports[0]);
    });
    // Only staff can list departments; employees simply get no filter.
    api.get("/org/departments").then((r) => setDepartments(r.data)).catch(() => {});
  }, []);

  function queryFor(spec: any) {
    const q: Record<string, unknown> = {};
    if (spec.params.includes("range")) {
      q.start = params.start;
      q.end = params.end;
    }
    if (spec.params.includes("month")) {
      q.month = Number(params.month);
      q.year = Number(params.year);
    }
    if (spec.params.includes("year") && !spec.params.includes("month")) q.year = Number(params.year);
    if (spec.params.includes("department") && params.department_id) q.department_id = Number(params.department_id);
    return q;
  }

  function runReport(e?: FormEvent) {
    e?.preventDefault();
    if (!selected) return;
    setLoading(true);
    setError("");
    api
      .get(`/reports/${selected.key}`, { params: queryFor(selected) })
      .then((r) => setReport(r.data))
      .catch((err) => {
        setReport(null);
        setError(apiErrorMessage(err));
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (selected) runReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const needs = (p: string) => selected?.params.includes(p);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-brand-dark">Reports</h1>
        <p className="text-sm text-slate-500 mt-1">
          Built from the same records as the dashboards, so the numbers always agree. Every report exports to CSV.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {available.map((r) => (
          <button
            key={r.key}
            onClick={() => setSelected(r)}
            className={`text-left border rounded-lg p-3 transition-colors ${
              selected?.key === r.key ? "border-brand bg-brand/5" : "bg-white hover:bg-slate-50"
            }`}
          >
            <div className="font-medium text-brand-dark">{r.title}</div>
            <div className="text-xs text-slate-500 mt-1">{r.description}</div>
          </button>
        ))}
      </div>

      {selected && (
        <form onSubmit={runReport} className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-3">
          {needs("range") && (
            <>
              <label className="text-sm">
                From
                <input type="date" className="block border rounded px-2 py-1" value={params.start} onChange={(e) => setParams({ ...params, start: e.target.value })} />
              </label>
              <label className="text-sm">
                To
                <input type="date" className="block border rounded px-2 py-1" value={params.end} onChange={(e) => setParams({ ...params, end: e.target.value })} />
              </label>
            </>
          )}
          {needs("month") && (
            <label className="text-sm">
              Month
              <input type="number" min={1} max={12} className="block border rounded px-2 py-1 w-20" value={params.month} onChange={(e) => setParams({ ...params, month: e.target.value })} />
            </label>
          )}
          {(needs("month") || needs("year")) && (
            <label className="text-sm">
              Year
              <input type="number" className="block border rounded px-2 py-1 w-28" value={params.year} onChange={(e) => setParams({ ...params, year: e.target.value })} />
            </label>
          )}
          {needs("department") && (
            <label className="text-sm">
              Department
              <select className="block border rounded px-2 py-1" value={params.department_id} onChange={(e) => setParams({ ...params, department_id: e.target.value })}>
                <option value="">All</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Run report</button>
          {report && report.rows.length > 0 && (
            <button
              type="button"
              className="text-sm text-brand underline"
              onClick={() => downloadCsv(`/reports/${selected.key}/export-csv`, `${selected.key}.csv`, queryFor(selected))}
            >
              Export CSV
            </button>
          )}
        </form>
      )}

      {error && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2">{error}</div>}
      {loading && <div className="text-sm text-slate-400">Running…</div>}

      {report && !loading && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-brand-dark">{report.title}</h2>
            <p className="text-xs text-slate-500 mt-0.5">{report.subtitle}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-left">
                <tr>
                  {report.columns.map((c: any) => (
                    <th key={c.key} className={`p-2 ${c.numeric ? "text-right" : ""}`}>
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.rows.map((row: any, i: number) => (
                  <tr key={i} className="border-t">
                    {report.columns.map((c: any) => (
                      <td key={c.key} className={`p-2 ${c.numeric ? "text-right tabular-nums" : ""}`}>
                        {row[c.key] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
                {report.rows.length === 0 && (
                  <tr>
                    <td className="p-4 text-slate-400" colSpan={report.columns.length}>
                      Nothing to report for this period.
                    </td>
                  </tr>
                )}
              </tbody>
              {report.totals && report.rows.length > 0 && (
                <tfoot>
                  <tr className="border-t-2 bg-slate-50 font-medium">
                    {report.columns.map((c: any) => (
                      <td key={c.key} className={`p-2 ${c.numeric ? "text-right tabular-nums" : ""}`}>
                        {report.totals[c.key] ?? ""}
                      </td>
                    ))}
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
