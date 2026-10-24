import { useCallback, useEffect, useState } from "react";
import api from "../../api/client";
import KpiCard from "../../components/KpiCard";
import AISummaryButton from "../../components/AISummaryButton";
import DashboardFilters, { FilterValues, defaultFilters, toParams } from "../../components/DashboardFilters";
import { BarCard, LineCard } from "../../components/Charts";

export default function HRDashboard() {
  const [filters, setFilters] = useState<FilterValues>(defaultFilters);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback((applied: FilterValues) => {
    setLoading(true);
    api
      .get("/dashboards/hr", { params: toParams(applied) })
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
      <h1 className="text-2xl font-bold text-brand-dark">HR dashboard</h1>

      <DashboardFilters value={filters} onApply={apply} />

      {loading && <div className="text-slate-400 text-sm">Loading…</div>}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <KpiCard label="Headcount" value={data.headcount} />
            <KpiCard label="Present today" value={data.present_today} />
            <KpiCard label="On leave today" value={data.on_leave_today} />
            <KpiCard label="Late today" value={data.late_today} />
            <KpiCard label="Attendance rate" value={`${data.attendance_rate}%`} />
            <KpiCard label="Pending approvals" value={data.pending_leave_approvals} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
            <BarCard
              title="Attendance rate by department"
              data={data.attendance_by_department}
              xKey="department"
              bars={[{ key: "attendance_rate", name: "Attendance %" }]}
            />
            <BarCard
              title="Absenteeism by department"
              data={data.attendance_by_department}
              xKey="department"
              bars={[{ key: "absenteeism_pct", name: "Absent %" }]}
            />
            <BarCard
              title="Leave days by type"
              data={data.leave_by_type}
              xKey="type"
              bars={[{ key: "days", name: "Approved days" }]}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-2">Top late-comers</h3>
              <ul className="text-sm space-y-1">
                {data.top_late_comers.map((t: any) => (
                  <li key={t.employee_id} className="flex justify-between">
                    <span>{t.name}</span>
                    <span className="text-slate-500">{t.late_count}×</span>
                  </li>
                ))}
                {data.top_late_comers.length === 0 && <li className="text-slate-400">No late check-ins in this range.</li>}
              </ul>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-2">Leave utilization</h3>
              <ul className="text-sm space-y-1">
                {data.leave_by_type.map((t: any) => (
                  <li key={t.type} className="flex justify-between">
                    <span className="capitalize">{t.type}</span>
                    <span className="text-slate-500">
                      {t.days} days{t.utilization_pct !== null ? ` · ${t.utilization_pct}% of quota` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <AISummaryButton kpiJson={data} />
        </>
      )}
    </div>
  );
}
