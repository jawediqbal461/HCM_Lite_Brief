import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { apiErrorMessage } from "../../api/client";

const BAND_STYLE: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-slate-100 text-slate-700",
};

export default function Insights({ employeeBase }: { employeeBase: string }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/dashboards/insights")
      .then((r) => setData(r.data))
      .catch((e) => setError(apiErrorMessage(e)));
  }, []);

  if (error) return <div className="text-red-600">{error}</div>;
  if (!data) return <div>Loading…</div>;

  const { attrition_risk: risk, absence_anomalies: anomalies, late_penalty: penalty } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-brand-dark">Insights</h1>
        <p className="text-sm text-slate-500 mt-1">
          Patterns in the last 90 days of records, as of {data.as_of}. These are signals to look into, not conclusions —
          every score shows the reasons behind it.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold">Attrition risk</h2>
        <p className="text-xs text-slate-400 mb-3">
          Weighted from absence, lateness, leave use and tenure. Nobody with a clean record appears here.
        </p>
        <div className="space-y-3">
          {risk.map((r: any) => (
            <div key={r.employee_id} className="border rounded p-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <Link to={`${employeeBase}/${r.employee_id}`} className="font-medium text-brand underline">
                    {r.name}
                  </Link>
                  <span className="text-xs text-slate-400 ml-2">{r.department || "No department"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded px-2 py-0.5 text-xs capitalize ${BAND_STYLE[r.band]}`}>{r.band} risk</span>
                  <span className="text-sm font-semibold text-brand-dark">{r.score}/100</span>
                </div>
              </div>
              <ul className="mt-2 space-y-1">
                {r.factors.map((f: string) => (
                  <li key={f} className="text-sm text-slate-600 flex gap-2">
                    <span className="text-slate-300">•</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {risk.length === 0 && (
            <div className="text-sm text-slate-400">No one is showing attrition signals in this window.</div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold">Absence anomalies</h2>
        <p className="text-xs text-slate-400 mb-3">
          Unusual shapes in attendance — not necessarily a problem, but worth a conversation.
        </p>
        <div className="space-y-3">
          {anomalies.map((a: any) => (
            <div key={a.employee_id} className="border rounded p-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <Link to={`${employeeBase}/${a.employee_id}`} className="font-medium text-brand underline">
                    {a.name}
                  </Link>
                  <span className="text-xs text-slate-400 ml-2">{a.department || "No department"}</span>
                </div>
                <span className="text-xs text-slate-500">
                  {a.absences} absences · {a.lates} lates
                </span>
              </div>
              <ul className="mt-2 space-y-1">
                {a.flags.map((f: any) => (
                  <li key={f.flag} className="text-sm">
                    <span className="font-medium text-slate-700">{f.label}</span>
                    <span className="text-slate-500"> — {f.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {anomalies.length === 0 && <div className="text-sm text-slate-400">No unusual absence patterns found.</div>}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold">Late penalty rule</h2>
        <p className="text-sm text-slate-600 mt-1">
          Every <strong>{penalty.lates_per_penalty} late arrivals</strong> in a month cost{" "}
          <strong>{penalty.penalty_days} of a day's pay</strong>. Partial groups do not count — two lates cost nothing.
          The deduction is applied when the monthly payroll is generated and shown as its own line on the payslip.
        </p>
      </div>
    </div>
  );
}
