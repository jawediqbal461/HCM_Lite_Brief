import { useEffect, useState } from "react";
import api from "../../api/client";

const STATUS_STYLES: Record<string, string> = {
  present: "bg-green-100 text-green-800",
  late: "bg-amber-100 text-amber-800",
  half_day: "bg-sky-100 text-sky-800",
  missing_checkout: "bg-orange-100 text-orange-800",
  on_leave: "bg-indigo-100 text-indigo-800",
  absent: "bg-red-100 text-red-800",
  weekend: "bg-slate-100 text-slate-500",
  holiday: "bg-slate-100 text-slate-500",
};

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[status] || "bg-slate-100 text-slate-600"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function AttendanceBoard({ canDecide }: { canDecide: boolean }) {
  const [day, setDay] = useState(todayISO);
  const [rows, setRows] = useState<any[]>([]);
  const [corrections, setCorrections] = useState<any[]>([]);

  function load(forDay: string) {
    api.get("/attendance/board", { params: { day: forDay } }).then((r) => setRows(r.data));
    api.get("/attendance/corrections/pending").then((r) => setCorrections(r.data));
  }
  useEffect(() => load(day), [day]);

  async function decide(id: number, approve: boolean) {
    await api.post(`/attendance/corrections/${id}/decide`, { approve });
    load(day);
  }

  const summary = rows.reduce<Record<string, number>>((acc, row) => {
    acc[row.status] = (acc[row.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-brand-dark">Daily attendance</h1>
        <label className="text-sm">
          Day{" "}
          <input type="date" className="border rounded px-2 py-1" value={day} onChange={(e) => setDay(e.target.value)} />
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(summary).map(([status, count]) => (
          <span key={status} className="text-xs">
            <StatusPill status={status} /> <span className="text-slate-500">{count}</span>
          </span>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Employee</th>
              <th className="p-2">Department</th>
              <th className="p-2">Check in</th>
              <th className="p-2">Check out</th>
              <th className="p-2">Status</th>
              <th className="p-2">Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.employee_id} className="border-t">
                <td className="p-2">
                  <div className="font-medium">{r.employee_name}</div>
                  <div className="text-xs text-slate-400">{r.employee_code}</div>
                </td>
                <td className="p-2">{r.department || "—"}</td>
                <td className="p-2">{r.check_in_time ? new Date(r.check_in_time).toLocaleTimeString() : "—"}</td>
                <td className="p-2">{r.check_out_time ? new Date(r.check_out_time).toLocaleTimeString() : "—"}</td>
                <td className="p-2">
                  <StatusPill status={r.status} />
                </td>
                <td className="p-2">{r.source || "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={6}>
                  No employees registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2 className="text-xl font-bold text-brand-dark">Pending corrections</h2>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Employee</th>
              <th className="p-2">Date</th>
              <th className="p-2">Reason</th>
              <th className="p-2">{canDecide ? "Decision" : "Status"}</th>
            </tr>
          </thead>
          <tbody>
            {corrections.map((c) => (
              <tr key={c.id} className="border-t">
                <td className="p-2">{c.employee_name || `#${c.employee_id}`}</td>
                <td className="p-2">{c.date}</td>
                <td className="p-2">{c.correction_reason}</td>
                <td className="p-2 space-x-2">
                  {canDecide ? (
                    <>
                      <button className="text-green-700" onClick={() => decide(c.id, true)}>
                        Approve
                      </button>
                      <button className="text-red-700" onClick={() => decide(c.id, false)}>
                        Reject
                      </button>
                    </>
                  ) : (
                    <span className="capitalize text-slate-500">{c.correction_status}</span>
                  )}
                </td>
              </tr>
            ))}
            {corrections.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={4}>
                  Nothing pending.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
