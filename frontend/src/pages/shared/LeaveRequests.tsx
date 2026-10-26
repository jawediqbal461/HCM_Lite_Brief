import { FormEvent, useCallback, useEffect, useState } from "react";
import api, { downloadCsv } from "../../api/client";
import Pagination from "../../components/Pagination";

const STATUSES = ["pending", "approved", "rejected", "cancelled"];
const PAGE_SIZE = 25;

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-slate-100 text-slate-600",
};

export default function LeaveRequests({ canDecide }: { canDecide: boolean }) {
  const [rows, setRows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [comment, setComment] = useState<Record<number, string>>({});
  const [departments, setDepartments] = useState<any[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<any[]>([]);
  const [filters, setFilters] = useState({ status: "", leave_type_id: "", department_id: "", start: "", end: "", search: "" });

  const params = (f = filters) => ({
    status: f.status || undefined,
    leave_type_id: f.leave_type_id ? Number(f.leave_type_id) : undefined,
    department_id: f.department_id ? Number(f.department_id) : undefined,
    start: f.start || undefined,
    end: f.end || undefined,
    search: f.search || undefined,
  });

  const load = useCallback(
    (toPage = 1, applied = filters) => {
      if (canDecide) {
        // The approval inbox is by definition the pending queue, and short.
        api.get("/leave/inbox").then((r) => {
          setRows(r.data);
          setTotal(r.data.length);
          setPage(1);
        });
        return;
      }
      api.get("/leave", { params: { ...params(applied), page: toPage, page_size: PAGE_SIZE } }).then((r) => {
        setRows(r.data.items);
        setTotal(r.data.total);
        setPage(r.data.page);
      });
    },
    [canDecide, filters],
  );

  useEffect(() => {
    load(1, filters);
    api.get("/org/leave-types").then((r) => setLeaveTypes(r.data)).catch(() => {});
    api.get("/org/departments").then((r) => setDepartments(r.data)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canDecide]);

  async function decide(id: number, approve: boolean) {
    await api.post(`/leave/${id}/decide`, { approve, comment: comment[id] || null });
    load(page, filters);
  }

  function apply(e: FormEvent) {
    e.preventDefault();
    load(1, filters);
  }

  function reset() {
    const cleared = { status: "", leave_type_id: "", department_id: "", start: "", end: "", search: "" };
    setFilters(cleared);
    load(1, cleared);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-brand-dark">{canDecide ? "Leave approvals" : "Leave records"}</h1>
        {!canDecide && (
          <button className="text-sm text-brand underline" onClick={() => downloadCsv("/leave/export-csv", "leave.csv", params())}>
            Export CSV
          </button>
        )}
      </div>

      {!canDecide && (
        <form onSubmit={apply} className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-3">
          <label className="text-sm">
            Search
            <input
              className="block border rounded px-2 py-1"
              placeholder="Name or code"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Status
            <select className="block border rounded px-2 py-1" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Type
            <select
              className="block border rounded px-2 py-1"
              value={filters.leave_type_id}
              onChange={(e) => setFilters({ ...filters, leave_type_id: e.target.value })}
            >
              <option value="">All</option>
              {leaveTypes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Department
            <select
              className="block border rounded px-2 py-1"
              value={filters.department_id}
              onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
            >
              <option value="">All</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
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
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Employee</th>
              <th className="p-2">Type</th>
              <th className="p-2">Dates</th>
              <th className="p-2">Days</th>
              <th className="p-2">Reason</th>
              {canDecide ? (
                <>
                  <th className="p-2">Comment</th>
                  <th className="p-2">Decision</th>
                </>
              ) : (
                <th className="p-2">Status</th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t align-top">
                <td className="p-2">{r.employee_name || `#${r.employee_id}`}</td>
                <td className="p-2 capitalize">{r.leave_type_name || "—"}</td>
                <td className="p-2">
                  {r.start_date} → {r.end_date}
                </td>
                <td className="p-2">{r.days}</td>
                <td className="p-2">{r.reason}</td>
                {canDecide ? (
                  <>
                    <td className="p-2">
                      <input
                        className="border rounded px-2 py-1 text-xs w-32"
                        placeholder="Optional"
                        onChange={(e) => setComment({ ...comment, [r.id]: e.target.value })}
                      />
                    </td>
                    <td className="p-2 space-x-2 whitespace-nowrap">
                      <button className="text-green-700" onClick={() => decide(r.id, true)}>
                        Approve
                      </button>
                      <button className="text-red-700" onClick={() => decide(r.id, false)}>
                        Reject
                      </button>
                    </td>
                  </>
                ) : (
                  <td className="p-2">
                    <span className={`rounded px-2 py-0.5 text-xs capitalize ${STATUS_STYLE[r.status] || ""}`}>{r.status}</span>
                  </td>
                )}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={canDecide ? 7 : 6}>
                  {canDecide ? "No pending requests." : "No leave records match these filters."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {!canDecide && <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={(p) => load(p, filters)} />}
      </div>
    </div>
  );
}
