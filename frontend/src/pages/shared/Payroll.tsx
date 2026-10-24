import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export default function Payroll() {
  const [runs, setRuns] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());
  const [msg, setMsg] = useState("");
  const { user } = useAuth();

  function load() {
    api.get("/payroll/runs").then((r) => setRuns(r.data));
  }
  useEffect(load, []);

  async function createDraft(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      const res = await api.post("/payroll/runs", { month: Number(month), year: Number(year) });
      setSelected(res.data);
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function downloadPayslip(payslipId: number) {
    const res = await api.get(`/payroll/payslips/${payslipId}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `payslip-${payslipId}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  async function finalize(id: number) {
    try {
      const res = await api.post(`/payroll/runs/${id}/finalize`);
      setSelected(res.data);
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">Payroll</h1>
      {msg && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2">{msg}</div>}

      {user?.role === "hr" && (
        <form onSubmit={createDraft} className="bg-white rounded-lg shadow p-4 flex items-end gap-3">
          <label className="text-sm">
            Month
            <input type="number" min={1} max={12} className="block border rounded px-2 py-1 w-20" value={month} onChange={(e) => setMonth(Number(e.target.value))} />
          </label>
          <label className="text-sm">
            Year
            <input type="number" className="block border rounded px-2 py-1 w-28" value={year} onChange={(e) => setYear(Number(e.target.value))} />
          </label>
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Create / refresh draft</button>
        </form>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-4 space-y-2 col-span-1">
          <h2 className="font-semibold">Runs</h2>
          {runs.map((r) => (
            <button
              key={r.id}
              onClick={() => setSelected(r)}
              className={`block w-full text-left px-2 py-1 rounded text-sm ${selected?.id === r.id ? "bg-brand/10" : "hover:bg-slate-50"}`}
            >
              {r.month}/{r.year} — {r.status}
            </button>
          ))}
        </div>

        <div className="bg-white rounded-lg shadow p-4 col-span-2">
          {!selected && <div className="text-slate-400 text-sm">Select a payroll run</div>}
          {selected && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h2 className="font-semibold">
                  {selected.month}/{selected.year} — {selected.status}
                </h2>
                {user?.role === "admin" && selected.status === "draft" && (
                  <button className="bg-brand text-white rounded px-4 py-1.5 text-sm" onClick={() => finalize(selected.id)}>
                    Finalize (locks the month)
                  </button>
                )}
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-100 text-left">
                  <tr>
                    <th className="p-2">Employee</th>
                    <th className="p-2">Gross</th>
                    <th className="p-2">Deductions</th>
                    <th className="p-2">Tax</th>
                    <th className="p-2">Net</th>
                    <th className="p-2">Payslip</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.payslips.map((p: any) => (
                    <tr key={p.id} className="border-t">
                      <td className="p-2">
                        <div className="font-medium">{p.employee_name || `#${p.employee_id}`}</div>
                        <div className="text-xs text-slate-400">{p.employee_code}</div>
                      </td>
                      <td className="p-2">{p.gross.toFixed(2)}</td>
                      <td className="p-2">{p.deductions.toFixed(2)}</td>
                      <td className="p-2">{p.tax.toFixed(2)}</td>
                      <td className="p-2 font-medium">{p.net_pay.toFixed(2)}</td>
                      <td className="p-2">
                        {selected.status === "finalized" ? (
                          <button className="text-brand underline" onClick={() => downloadPayslip(p.id)}>
                            PDF
                          </button>
                        ) : (
                          <span className="text-slate-400 text-xs">after finalize</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
