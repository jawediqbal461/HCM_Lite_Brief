import { useEffect, useState } from "react";
import api from "../../api/client";

export default function MyPayslips() {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    api.get("/payroll/payslips/mine").then((r) => setItems(r.data));
  }, []);

  async function download(id: number) {
    const res = await api.get(`/payroll/payslips/${id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `payslip-${id}.pdf`;
    link.click();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-brand-dark">My payslips</h1>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Run</th>
              <th className="p-2">Gross</th>
              <th className="p-2">Net pay</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className="border-t">
                <td className="p-2">#{p.payroll_run_id}</td>
                <td className="p-2">{p.gross.toFixed(2)}</td>
                <td className="p-2 font-medium">{p.net_pay.toFixed(2)}</td>
                <td className="p-2">
                  <button className="text-brand underline" onClick={() => download(p.id)}>
                    Download PDF
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={4}>
                  No finalized payslips yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
