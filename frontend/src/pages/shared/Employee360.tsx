import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../../api/client";
import KpiCard from "../../components/KpiCard";

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function Employee360({ backTo }: { backTo: string }) {
  const { id } = useParams();
  const [employee, setEmployee] = useState<any>(null);
  const [attendance, setAttendance] = useState<any[]>([]);
  const [leave, setLeave] = useState<any[]>([]);
  const [payslips, setPayslips] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    api
      .get(`/employees/${id}`)
      .then((r) => setEmployee(r.data))
      .catch(() => setError("Could not load this employee."));
    api
      .get("/attendance/calendar", { params: { employee_id: id, start: isoDaysAgo(30), end: isoDaysAgo(0) } })
      .then((r) => setAttendance(r.data))
      .catch(() => setAttendance([]));
    api
      .get("/leave", { params: { employee_id: id } })
      .then((r) => setLeave(r.data))
      .catch(() => setLeave([]));
    api
      .get("/payroll/payslips", { params: { employee_id: id } })
      .then((r) => setPayslips(r.data))
      .catch(() => setPayslips([]));
  }, [id]);

  async function downloadPayslip(payslipId: number) {
    const res = await api.get(`/payroll/payslips/${payslipId}/pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `payslip-${payslipId}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  if (error) return <div className="text-red-600">{error}</div>;
  if (!employee) return <div>Loading...</div>;

  const lateCount = attendance.filter((a) => a.status === "late").length;
  const approvedLeaveDays = leave.filter((l) => l.status === "approved").reduce((sum, l) => sum + l.days, 0);

  return (
    <div className="space-y-6">
      <Link to={backTo} className="text-sm text-brand underline">
        ← Back to employees
      </Link>

      <div className="bg-white rounded-lg shadow p-4">
        <h1 className="text-2xl font-bold text-brand-dark">{employee.full_name}</h1>
        <div className="text-sm text-slate-500">
          {employee.code} · {employee.email}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-sm">
          <div>
            <span className="text-slate-500">Status:</span> <span className="capitalize">{employee.status}</span>
          </div>
          <div>
            <span className="text-slate-500">Joined:</span> {employee.date_of_joining}
          </div>
          <div>
            <span className="text-slate-500">Phone:</span> {employee.phone || "—"}
          </div>
          <div>
            <span className="text-slate-500">Gender:</span> {employee.gender || "—"}
          </div>
          <div className="md:col-span-4">
            <span className="text-slate-500">Address:</span> {employee.address || "—"}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Basic salary" value={Math.round(employee.basic_salary).toLocaleString()} />
        <KpiCard label="Late (last 30 days)" value={lateCount} />
        <KpiCard label="Approved leave days" value={approvedLeaveDays} />
        <KpiCard label="Payslips" value={payslips.length} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Attendance (last 30 days)</h2>
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="p-2">Date</th>
                <th className="p-2">In</th>
                <th className="p-2">Out</th>
                <th className="p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {attendance.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="p-2">{a.date}</td>
                  <td className="p-2">{a.check_in_time ? new Date(a.check_in_time).toLocaleTimeString() : "—"}</td>
                  <td className="p-2">{a.check_out_time ? new Date(a.check_out_time).toLocaleTimeString() : "—"}</td>
                  <td className="p-2 capitalize">{a.status.replace("_", " ")}</td>
                </tr>
              ))}
              {attendance.length === 0 && (
                <tr>
                  <td className="p-4 text-slate-400" colSpan={4}>
                    No attendance records in this window.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-2">Leave history</h2>
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left">
              <tr>
                <th className="p-2">Type</th>
                <th className="p-2">Dates</th>
                <th className="p-2">Days</th>
                <th className="p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {leave.map((l) => (
                <tr key={l.id} className="border-t">
                  <td className="p-2 capitalize">{l.leave_type_name || "—"}</td>
                  <td className="p-2">
                    {l.start_date} → {l.end_date}
                  </td>
                  <td className="p-2">{l.days}</td>
                  <td className="p-2 capitalize">{l.status}</td>
                </tr>
              ))}
              {leave.length === 0 && (
                <tr>
                  <td className="p-4 text-slate-400" colSpan={4}>
                    No leave requests yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Payslips</h2>
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Run</th>
              <th className="p-2">Gross</th>
              <th className="p-2">Deductions</th>
              <th className="p-2">Net</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {payslips.map((p) => (
              <tr key={p.id} className="border-t">
                <td className="p-2">#{p.payroll_run_id}</td>
                <td className="p-2">{p.gross.toFixed(2)}</td>
                <td className="p-2">{p.deductions.toFixed(2)}</td>
                <td className="p-2 font-medium">{p.net_pay.toFixed(2)}</td>
                <td className="p-2">
                  <button className="text-brand underline" onClick={() => downloadPayslip(p.id)}>
                    PDF
                  </button>
                </td>
              </tr>
            ))}
            {payslips.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={5}>
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
