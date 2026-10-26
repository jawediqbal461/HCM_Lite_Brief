import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../api/client";

const STATUSES = ["active", "probation", "exited"];

export default function EmployeeEditForm({
  employee,
  onSaved,
  onCancel,
}: {
  employee: any;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [departments, setDepartments] = useState<any[]>([]);
  const [designations, setDesignations] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    full_name: employee.full_name || "",
    phone: employee.phone || "",
    address: employee.address || "",
    gender: employee.gender || "",
    department_id: employee.department_id ? String(employee.department_id) : "",
    designation_id: employee.designation_id ? String(employee.designation_id) : "",
    status: employee.status || "active",
    basic_salary: String(employee.basic_salary ?? ""),
    date_of_leaving: employee.date_of_leaving || "",
  });

  useEffect(() => {
    api.get("/org/departments").then((r) => setDepartments(r.data)).catch(() => {});
    api.get("/org/designations").then((r) => setDesignations(r.data)).catch(() => {});
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await api.patch(`/employees/${employee.id}`, {
        full_name: form.full_name,
        phone: form.phone || null,
        address: form.address || null,
        gender: form.gender || null,
        department_id: form.department_id ? Number(form.department_id) : null,
        designation_id: form.designation_id ? Number(form.designation_id) : null,
        status: form.status,
        basic_salary: form.basic_salary ? Number(form.basic_salary) : null,
        date_of_leaving: form.date_of_leaving || null,
      });
      onSaved();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="bg-white border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">
          Edit {employee.full_name} <span className="text-xs text-slate-400">({employee.code})</span>
        </h3>
        <button type="button" className="text-sm text-slate-500 underline" onClick={onCancel}>
          Cancel
        </button>
      </div>

      {error && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
        <label>
          Full name
          <input
            className="w-full border rounded px-2 py-1"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
        </label>
        <label>
          Phone
          <input className="w-full border rounded px-2 py-1" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </label>
        <label>
          Gender
          <select className="w-full border rounded px-2 py-1" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
            <option value="">Not specified</option>
            <option value="Female">Female</option>
            <option value="Male">Male</option>
            <option value="Other">Other</option>
          </select>
        </label>

        <label>
          Department
          <select
            className="w-full border rounded px-2 py-1"
            value={form.department_id}
            onChange={(e) => setForm({ ...form, department_id: e.target.value })}
          >
            <option value="">None</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Designation
          <select
            className="w-full border rounded px-2 py-1"
            value={form.designation_id}
            onChange={(e) => setForm({ ...form, designation_id: e.target.value })}
          >
            <option value="">None</option>
            {designations.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select className="w-full border rounded px-2 py-1" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label>
          Basic salary
          <input
            className="w-full border rounded px-2 py-1"
            value={form.basic_salary}
            onChange={(e) => setForm({ ...form, basic_salary: e.target.value })}
          />
        </label>
        <label>
          Date of leaving
          <input
            type="date"
            className="w-full border rounded px-2 py-1"
            value={form.date_of_leaving}
            onChange={(e) => setForm({ ...form, date_of_leaving: e.target.value })}
          />
        </label>
        <label className="md:col-span-1">
          Address
          <input className="w-full border rounded px-2 py-1" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        </label>
      </div>

      <p className="text-xs text-slate-400">
        Salary changes apply to payroll runs generated from now on. A run that has been finalized stays locked.
      </p>

      <button className="bg-brand text-white rounded px-4 py-1.5 text-sm disabled:opacity-50" disabled={saving}>
        {saving ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}
