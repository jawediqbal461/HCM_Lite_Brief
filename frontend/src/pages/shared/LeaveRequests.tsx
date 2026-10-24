import { useEffect, useState } from "react";
import api from "../../api/client";

export default function LeaveRequests({ canDecide }: { canDecide: boolean }) {
  const [rows, setRows] = useState<any[]>([]);
  const [comment, setComment] = useState<Record<number, string>>({});

  function load() {
    api.get(canDecide ? "/leave/inbox" : "/leave").then((r) => setRows(r.data));
  }
  useEffect(load, [canDecide]);

  async function decide(id: number, approve: boolean) {
    await api.post(`/leave/${id}/decide`, { approve, comment: comment[id] || null });
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-brand-dark">{canDecide ? "Leave approvals" : "Leave records"}</h1>
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
                    <td className="p-2 space-x-2">
                      <button className="text-green-700" onClick={() => decide(r.id, true)}>
                        Approve
                      </button>
                      <button className="text-red-700" onClick={() => decide(r.id, false)}>
                        Reject
                      </button>
                    </td>
                  </>
                ) : (
                  <td className="p-2 capitalize">{r.status}</td>
                )}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={canDecide ? 7 : 6}>
                  {canDecide ? "No pending requests." : "No leave records yet."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
