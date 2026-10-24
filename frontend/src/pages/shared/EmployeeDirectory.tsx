import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { apiErrorMessage } from "../../api/client";

export default function EmployeeDirectory({ canManage, detailBase }: { canManage: boolean; detailBase: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [departments, setDepartments] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    code: "",
    full_name: "",
    email: "",
    phone: "",
    gender: "",
    department_id: "",
    date_of_joining: "",
    basic_salary: "",
  });
  const [csvErrors, setCsvErrors] = useState<any[] | null>(null);

  function load() {
    api.get("/employees", { params: { search: search || undefined } }).then((r) => setItems(r.data.items));
  }

  useEffect(() => {
    load();
    api.get("/org/departments").then((r) => setDepartments(r.data));
  }, []);

  async function search_() {
    load();
  }

  async function register(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      const res = await api.post("/employees", {
        ...form,
        gender: form.gender || null,
        department_id: form.department_id ? Number(form.department_id) : null,
        basic_salary: Number(form.basic_salary),
      });
      setMsg(`Registered ${res.data.employee.full_name}. Temporary password: ${res.data.temporary_password}`);
      setForm({ code: "", full_name: "", email: "", phone: "", gender: "", department_id: "", date_of_joining: "", basic_salary: "" });
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function dryRun(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const data = new FormData();
    data.append("file", file);
    const res = await api.post("/employees/import-csv/dry-run", data);
    const errors = res.data.rows.filter((r: any) => !r.ok);
    setCsvErrors(errors);
    if (errors.length === 0) {
      await api.post("/employees/import-csv", data);
      setMsg("CSV imported successfully");
      load();
    }
  }

  async function exportCsv() {
    const res = await api.get("/employees/export-csv", { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "employees.csv";
    link.click();
    window.URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-brand-dark">Employees</h1>
        {canManage && (
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Close" : "Register employee"}
          </button>
        )}
      </div>

      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2">{msg}</div>}

      {canManage && showForm && (
        <form onSubmit={register} className="bg-white rounded-lg shadow p-4 grid grid-cols-3 gap-3">
          <input className="border rounded px-2 py-1 text-sm" placeholder="Code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required />
          <input className="border rounded px-2 py-1 text-sm" placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          <input type="email" className="border rounded px-2 py-1 text-sm" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <input className="border rounded px-2 py-1 text-sm" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          <select className="border rounded px-2 py-1 text-sm" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
            <option value="">Gender (optional)</option>
            <option value="Female">Female</option>
            <option value="Male">Male</option>
            <option value="Other">Other</option>
          </select>
          <select className="border rounded px-2 py-1 text-sm" value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
            <option value="">Department</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <input type="date" className="border rounded px-2 py-1 text-sm" value={form.date_of_joining} onChange={(e) => setForm({ ...form, date_of_joining: e.target.value })} required />
          <input className="border rounded px-2 py-1 text-sm" placeholder="Basic salary" value={form.basic_salary} onChange={(e) => setForm({ ...form, basic_salary: e.target.value })} required />
          <button className="col-span-3 bg-brand text-white rounded px-4 py-1.5 text-sm">Register</button>
        </form>
      )}

      {canManage && (
        <div className="bg-white rounded-lg shadow p-4 flex items-center gap-4">
          <label className="text-sm font-medium">CSV import</label>
          <input type="file" accept=".csv" onChange={dryRun} className="text-sm" />
          <button className="text-sm text-brand underline" onClick={exportCsv}>
            Export CSV
          </button>
        </div>
      )}
      {csvErrors && csvErrors.length > 0 && (
        <div className="bg-red-50 text-red-700 rounded p-3 text-sm">
          {csvErrors.map((e, i) => (
            <div key={i}>
              Row {e.row}: {e.field} — {e.reason}
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input className="border rounded px-2 py-1 text-sm flex-1" placeholder="Search by name, code, email" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button className="bg-brand text-white rounded px-4 text-sm" onClick={search_}>
          Search
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Code</th>
              <th className="p-2">Name</th>
              <th className="p-2">Email</th>
              <th className="p-2">Status</th>
              <th className="p-2">Joined</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e) => (
              <tr key={e.id} className="border-t hover:bg-slate-50">
                <td className="p-2">{e.code}</td>
                <td className="p-2">
                  <Link to={`${detailBase}/${e.id}`} className="text-brand underline">
                    {e.full_name}
                  </Link>
                </td>
                <td className="p-2">{e.email}</td>
                <td className="p-2 capitalize">{e.status}</td>
                <td className="p-2">{e.date_of_joining}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
