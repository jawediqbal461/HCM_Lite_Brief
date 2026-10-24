import { useCallback, useEffect, useState } from "react";
import api from "../../api/client";
import KpiCard from "../../components/KpiCard";
import AISummaryButton from "../../components/AISummaryButton";
import DashboardFilters, { FilterValues, defaultFilters, toParams } from "../../components/DashboardFilters";
import { BarCard, LineCard, PieCard } from "../../components/Charts";

export default function AdminDashboard() {
  const [filters, setFilters] = useState<FilterValues>(defaultFilters);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback((applied: FilterValues) => {
    setLoading(true);
    api
      .get("/dashboards/admin", { params: toParams(applied) })
      .then((res) => setData(res.data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(filters);
  }, [load]);

  function apply(next: FilterValues) {
    setFilters(next);
    load(next);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">Company dashboard</h1>

      <DashboardFilters value={filters} onApply={apply} />

      {loading && <div className="text-slate-400 text-sm">Loading…</div>}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <KpiCard label="Headcount" value={data.headcount} />
            <KpiCard label="Attrition" value={`${data.attrition_pct}%`} />
            <KpiCard label="Payroll cost" value={Math.round(data.payroll_cost).toLocaleString()} />
            <KpiCard label="Avg salary" value={Math.round(data.avg_salary).toLocaleString()} />
            <KpiCard label="Attendance rate" value={`${data.attendance_rate}%`} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <BarCard
              title="Headcount by department"
              data={data.headcount_by_department}
              xKey="department"
              bars={[{ key: "headcount", name: "Employees" }]}
            />
            <BarCard
              title="Payroll cost by department"
              data={data.payroll_cost_by_department}
              xKey="department"
              bars={[{ key: "cost", name: "Net pay" }]}
            />
            <LineCard
              title="Attendance trend"
              data={data.trend}
              xKey="date"
              lines={[
                { key: "present", name: "Present" },
                { key: "late", name: "Late" },
                { key: "absent", name: "Absent" },
              ]}
            />
            <PieCard title="Gender" data={data.gender_breakdown} nameKey="gender" valueKey="count" />
            <BarCard
              title="Tenure"
              data={data.tenure_breakdown}
              xKey="bucket"
              bars={[{ key: "count", name: "Employees" }]}
            />
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-2">Recent activity</h3>
              <ul className="text-sm space-y-1 max-h-[220px] overflow-y-auto">
                {data.recent_audit.map((a: any) => (
                  <li key={a.id} className="flex justify-between gap-2">
                    <span className="capitalize">
                      {a.action} {a.entity.replace("_", " ")} #{a.entity_id}
                    </span>
                    <span className="text-slate-400 whitespace-nowrap">
                      {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
                    </span>
                  </li>
                ))}
                {data.recent_audit.length === 0 && <li className="text-slate-400">Nothing logged yet.</li>}
              </ul>
            </div>
          </div>

          <AISummaryButton kpiJson={data} />
        </>
      )}
    </div>
  );
}
