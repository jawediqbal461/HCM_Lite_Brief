import { FormEvent, useCallback, useEffect, useState } from "react";
import api, { downloadCsv } from "../../api/client";
import Pagination from "../../components/Pagination";

const PAGE_SIZE = 50;

export default function AuditLog() {
  const [rows, setRows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [options, setOptions] = useState<{ actions: string[]; entities: string[] }>({ actions: [], entities: [] });
  const [filters, setFilters] = useState({ action: "", entity: "", start: "", end: "" });

  const params = (f = filters) => ({
    action: f.action || undefined,
    entity: f.entity || undefined,
    start: f.start || undefined,
    end: f.end || undefined,
  });

  const load = useCallback(
    (toPage = 1, applied = filters) => {
      api.get("/audit-log", { params: { ...params(applied), page: toPage, page_size: PAGE_SIZE } }).then((r) => {
        setRows(r.data.items);
        setTotal(r.data.total);
        setPage(r.data.page);
      });
    },
    [filters],
  );

  useEffect(() => {
    load(1, filters);
    api.get("/audit-log/filters").then((r) => setOptions(r.data)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function apply(e: FormEvent) {
    e.preventDefault();
    load(1, filters);
  }

  function reset() {
    const cleared = { action: "", entity: "", start: "", end: "" };
    setFilters(cleared);
    load(1, cleared);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-brand-dark">Audit log</h1>
        <button className="text-sm text-brand underline" onClick={() => downloadCsv("/audit-log/export-csv", "audit-log.csv", params())}>
          Export CSV
        </button>
      </div>

      <form onSubmit={apply} className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Action
          <select className="block border rounded px-2 py-1" value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })}>
            <option value="">All</option>
            {options.actions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Entity
          <select className="block border rounded px-2 py-1" value={filters.entity} onChange={(e) => setFilters({ ...filters, entity: e.target.value })}>
            <option value="">All</option>
            {options.entities.map((en) => (
              <option key={en} value={en}>
                {en.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          From
          <input type="date" className="block border rounded px-2 py-1" value={filters.start} onChange={(e) => setFilters({ ...filters, start: e.target.value })} />
        </label>
        <label className="text-sm">
          To
          <input type="date" className="block border rounded px-2 py-1" value={filters.end} onChange={(e) => setFilters({ ...filters, end: e.target.value })} />
        </label>
        <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Apply</button>
        <button type="button" className="text-sm text-slate-500 underline" onClick={reset}>
          Reset
        </button>
      </form>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">When</th>
              <th className="p-2">Actor</th>
              <th className="p-2">Action</th>
              <th className="p-2">Entity</th>
              <th className="p-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="p-2 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
                <td className="p-2">{r.actor_id ?? "system"}</td>
                <td className="p-2 capitalize">{r.action}</td>
                <td className="p-2">
                  {r.entity.replace("_", " ")} #{r.entity_id}
                </td>
                <td className="p-2 font-mono text-xs max-w-md truncate" title={r.after_json || ""}>
                  {r.after_json}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={5}>
                  Nothing matches these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={(p) => load(p, filters)} />
      </div>
    </div>
  );
}
