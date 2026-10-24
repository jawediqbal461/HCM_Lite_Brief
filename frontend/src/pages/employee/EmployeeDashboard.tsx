import { useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";
import KpiCard from "../../components/KpiCard";

export default function EmployeeDashboard() {
  const [data, setData] = useState<any>(null);
  const [balance, setBalance] = useState<any[]>([]);
  const [announcements, setAnnouncements] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  function load() {
    api.get("/dashboards/me").then((res) => setData(res.data));
    api.get("/leave/balance").then((res) => setBalance(res.data));
    api.get("/announcements").then((res) => setAnnouncements(res.data));
  }
  useEffect(load, []);

  async function checkIn() {
    setMsg("");
    try {
      await api.post("/attendance/check-in", { source: "web" });
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function checkOut() {
    setMsg("");
    try {
      await api.post("/attendance/check-out");
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function downloadLastPayslip() {
    const res = await api.get(`/payroll/payslips/${data.last_payslip_id}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "payslip.pdf";
    link.click();
    window.URL.revokeObjectURL(url);
  }

  if (!data) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">My dashboard</h1>
      {msg && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2">{msg}</div>}

      <div className="bg-white rounded-lg shadow p-4 flex flex-wrap items-center gap-4">
        <div className="text-sm">
          Today:{" "}
          <span className="font-medium capitalize">
            {data.today_status ? data.today_status.replace("_", " ") : "not checked in"}
          </span>
        </div>
        <button
          className="bg-brand text-white rounded px-4 py-1.5 text-sm disabled:opacity-40"
          onClick={checkIn}
          disabled={data.checked_in}
        >
          Check in
        </button>
        <button
          className="bg-slate-700 text-white rounded px-4 py-1.5 text-sm disabled:opacity-40"
          onClick={checkOut}
          disabled={!data.checked_in || data.checked_out}
        >
          Check out
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard label="Hours this week (of 40)" value={data.hours_this_week} />
        <KpiCard label="Late this month" value={data.late_count_this_month} />
        <KpiCard
          label="Last payslip net"
          value={data.last_payslip_net ? Math.round(data.last_payslip_net).toLocaleString() : "—"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold mb-2">Leave balance</h3>
          <ul className="text-sm space-y-1">
            {balance.map((b) => (
              <li key={b.leave_type_id} className="flex justify-between">
                <span className="capitalize">{b.leave_type_name}</span>
                <span className="text-slate-500">
                  {b.remaining === null ? "unlimited" : `${b.remaining} of ${b.quota} left`}
                </span>
              </li>
            ))}
          </ul>
          {data.last_payslip_id && (
            <button className="mt-3 text-sm text-brand underline" onClick={downloadLastPayslip}>
              Download last payslip
            </button>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold mb-2">Announcements</h3>
          <ul className="text-sm space-y-2 max-h-56 overflow-y-auto">
            {announcements.map((a) => (
              <li key={a.id}>
                <div className="font-medium">{a.title}</div>
                <div className="text-slate-600">{a.body}</div>
              </li>
            ))}
            {announcements.length === 0 && <li className="text-slate-400">Nothing posted yet.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
