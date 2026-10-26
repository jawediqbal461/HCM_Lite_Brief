import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { apiErrorMessage, downloadCsv } from "../../api/client";
import Pagination from "../../components/Pagination";
import EmployeeEditForm from "../../components/EmployeeEditForm";

const STATUSES = ["active", "probation", "exited"];
const PAGE_SIZE = 20;

export default function EmployeeDirectory({ canManage, detailBase }: { canManage: boolean; detailBase: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [filters, setFilters] = useState({ search: "", department_id: "", status_: "" });
  const [departments, setDepartments] = useState<any[]>([]);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [csvErrors, setCsvErrors] = useState<any[] | null>(null);

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

  const load = useCallback(
    (toPage = page, applied = filters) => {
      setLoading(true);
      api
        .get("/employees", {
          params: {
            search: applied.search || undefined,
            department_id: applied.department_id ? Number(applied.department_id) : undefined,
            status_: applied.status_ || undefined,
            page: toPage,
            page_size: PAGE_SIZE,
          },
        })
        .then((r) => {
          setItems(r.data.items);
          setTotal(r.data.total);
          setPage(r.data.page);
        })
        .finally(() => setLoading(false));
    },
    [page, filters],
  );

  useEffect(() => {
    load(1, filters);
    api.get("/org/departments").then((r) => setDepartments(r.data)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyFilters(e: FormEvent) {
    e.preventDefault();
    load(1, filters);
  }

  function resetFilters() {
    const cleared = { search: "", department_id: "", status_: "" };
    setFilters(cleared);
    load(1, cleared);
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
      setShowForm(false);
      load(1, filters);
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
      load(1, filters);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold text-brand-dark">Employees</h1>
        <div className="flex items-center gap-3">
          {canManage && (
            <button className="text-sm text-brand underline" onClick={() => downloadCsv("/employees/export-csv", "employees.csv")}>
              Export CSV
            </button>
          )}
          {canManage && (
            <button
              className="bg-brand text-white rounded px-4 py-1.5 text-sm"
              onClick={() => {
                setShowForm((s) => !s);
                setEditing(null);
              }}
            >
              {showForm ? "Close" : "Register employee"}
            </button>
          )}
        </div>
      </div>

      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2 break-all">{msg}</div>}

      {canManage && editing && (
        <EmployeeEditForm
          employee={editing}
          onCancel={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setMsg("Employee updated.");
            load(page, filters);
          }}
        />
      )}

      {canManage && showForm && (
        <form onSubmit={register} className="bg-white rounded-lg shadow p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
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
          <button className="md:col-span-3 bg-brand text-white rounded px-4 py-1.5 text-sm">Register</button>
        </form>
      )}

      {canManage && (
        <div className="bg-white rounded-lg shadow p-4 flex items-center gap-4 flex-wrap">
          <label className="text-sm font-medium">CSV import</label>
          <input type="file" accept=".csv" onChange={dryRun} className="text-sm" />
          <span className="text-xs text-slate-400">Checked row by row first — nothing imports unless every row is valid.</span>
        </div>
      )}
      {csvErrors && csvErrors.length > 0 && (
        <div className="bg-red-50 text-red-700 rounded p-3 text-sm space-y-1">
          {csvErrors.map((e, i) => (
            <div key={i}>
              Row {e.row}: {e.field} — {e.reason}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={applyFilters} className="bg-white rounded-lg shadow p-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Search
          <input
            className="block border rounded px-2 py-1"
            placeholder="Name, code or email"
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
        </label>
        <label className="text-sm">
          Department
          <select
            className="block border rounded px-2 py-1"
            value={filters.department_id}
            onChange={(e) => setFilters({ ...filters, department_id: e.target.value })}
          >
            <option value="">All</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Status
          <select
            className="block border rounded px-2 py-1"
            value={filters.status_}
            onChange={(e) => setFilters({ ...filters, status_: e.target.value })}
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Apply</button>
        <button type="button" className="text-sm text-slate-500 underline" onClick={resetFilters}>
          Reset
        </button>
      </form>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Code</th>
              <th className="p-2">Name</th>
              <th className="p-2">Email</th>
              <th className="p-2">Status</th>
              <th className="p-2">Joined</th>
              <th className="p-2">Salary</th>
              {canManage && <th className="p-2"></th>}
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
                <td className="p-2">{Math.round(e.basic_salary).toLocaleString()}</td>
                {canManage && (
                  <td className="p-2">
                    <button
                      className="text-brand underline"
                      onClick={() => {
                        setEditing(e);
                        setShowForm(false);
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }}
                    >
                      Edit
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={canManage ? 7 : 6}>
                  No employees match these filters.
                </td>
              </tr>
            )}
            {loading && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={canManage ? 7 : 6}>
                  Loading…
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPage={(p) => load(p, filters)} />
      </div>
    </div>
  );
}
