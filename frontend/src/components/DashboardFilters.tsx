import { FormEvent, useEffect, useState } from "react";
import api from "../api/client";

export interface FilterValues {
  start: string;
  end: string;
  departmentId: string;
}

export function defaultFilters(): FilterValues {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
    departmentId: "",
  };
}

export function toParams(filters: FilterValues) {
  return {
    start: filters.start || undefined,
    end: filters.end || undefined,
    department_id: filters.departmentId ? Number(filters.departmentId) : undefined,
  };
}

export default function DashboardFilters({
  value,
  onApply,
}: {
  value: FilterValues;
  onApply: (next: FilterValues) => void;
}) {
  const [local, setLocal] = useState<FilterValues>(value);
  const [departments, setDepartments] = useState<any[]>([]);

  useEffect(() => {
    api
      .get("/org/departments")
      .then((r) => setDepartments(r.data))
      .catch(() => setDepartments([]));
  }, []);

  function submit(e: FormEvent) {
    e.preventDefault();
    onApply(local);
  }

  function reset() {
    const defaults = defaultFilters();
    setLocal(defaults);
    onApply(defaults);
  }

  return (
    <form onSubmit={submit} className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-3">
      <label className="text-sm">
        From
        <input
          type="date"
          className="block border rounded px-2 py-1"
          value={local.start}
          onChange={(e) => setLocal({ ...local, start: e.target.value })}
        />
      </label>
      <label className="text-sm">
        To
        <input
          type="date"
          className="block border rounded px-2 py-1"
          value={local.end}
          onChange={(e) => setLocal({ ...local, end: e.target.value })}
        />
      </label>
      <label className="text-sm">
        Department
        <select
          className="block border rounded px-2 py-1"
          value={local.departmentId}
          onChange={(e) => setLocal({ ...local, departmentId: e.target.value })}
        >
          <option value="">All departments</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <button className="bg-brand text-white rounded px-4 py-1.5 text-sm" type="submit">
        Apply
      </button>
      <button type="button" className="text-sm text-slate-500 underline" onClick={reset}>
        Reset
      </button>
    </form>
  );
}
