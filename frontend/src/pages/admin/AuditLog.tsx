import { useEffect, useState } from "react";
import api from "../../api/client";

export default function AuditLog() {
  const [rows, setRows] = useState<any[]>([]);

  useEffect(() => {
    api.get("/audit-log").then((r) => setRows(r.data));
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-brand-dark">Audit log</h1>
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
                <td className="p-2">{r.action}</td>
                <td className="p-2">
                  {r.entity} #{r.entity_id}
                </td>
                <td className="p-2 font-mono text-xs">{r.after_json}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
