import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";

const ROLES = ["admin", "hr", "employee"];

const ROLE_STYLE: Record<string, string> = {
  admin: "bg-indigo-100 text-indigo-800",
  hr: "bg-sky-100 text-sky-800",
  employee: "bg-slate-100 text-slate-700",
};

export default function UserAccess() {
  const [users, setUsers] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState({ full_name: "", email: "", password: "", require_password_change: true });

  function load() {
    api
      .get("/org/users")
      .then((r) => setUsers(r.data))
      .catch((e) => setError(apiErrorMessage(e)));
  }
  useEffect(load, []);

  function run(action: Promise<any>, okMsg: string) {
    setMsg("");
    setError("");
    action
      .then(() => {
        setMsg(okMsg);
        load();
      })
      .catch((e) => setError(apiErrorMessage(e)));
  }

  async function createHr(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    setError("");
    try {
      await api.post("/org/hr-users", form);
      setMsg(
        form.require_password_change
          ? `HR login created for ${form.email}. They must change this password on first sign-in.`
          : `HR login created for ${form.email}. The password stays as set — fine for a shared demo login, change it afterwards.`,
      );
      setForm({ full_name: "", email: "", password: "", require_password_change: true });
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function resetPassword(user: any) {
    setMsg("");
    setError("");
    try {
      const res = await api.post(`/org/users/${user.id}/reset-password`);
      setMsg(`Temporary password for ${user.email}: ${res.data.temporary_password} — copy it now, it is not shown again.`);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">Users &amp; access</h1>
      <p className="text-sm text-slate-500">
        Every login in the system. Employee logins are created automatically when HR registers someone; HR logins are
        created here.
      </p>

      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2 break-all">{msg}</div>}
      {error && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2">{error}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Login</th>
              <th className="p-2">Role</th>
              <th className="p-2">Status</th>
              <th className="p-2">Change role</th>
              <th className="p-2">Credentials</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t align-middle">
                <td className="p-2">
                  <div className="font-medium">{u.employee_name || u.email}</div>
                  <div className="text-xs text-slate-400">
                    {u.employee_name ? u.email : "no employee record"}
                    {u.employee_code ? ` · ${u.employee_code}` : ""}
                  </div>
                </td>
                <td className="p-2">
                  <span className={`rounded px-2 py-0.5 text-xs capitalize ${ROLE_STYLE[u.role]}`}>{u.role}</span>
                </td>
                <td className="p-2">
                  {u.is_active ? (
                    <span className="text-green-700">Active</span>
                  ) : (
                    <span className="text-red-700">Deactivated</span>
                  )}
                  {u.must_change_password && <div className="text-xs text-amber-600">must change password</div>}
                </td>
                <td className="p-2">
                  <select
                    className="border rounded px-2 py-1 text-xs"
                    value={u.role}
                    onChange={(e) =>
                      run(
                        api.patch(`/org/users/${u.id}/role`, { role: e.target.value }),
                        `${u.email} is now ${e.target.value}.`,
                      )
                    }
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="p-2 space-x-3 whitespace-nowrap">
                  <button className="text-brand underline" onClick={() => resetPassword(u)}>
                    Reset password
                  </button>
                  {u.is_active ? (
                    <button
                      className="text-red-700 underline"
                      onClick={() => run(api.post(`/org/users/${u.id}/deactivate`), `${u.email} deactivated.`)}
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button
                      className="text-green-700 underline"
                      onClick={() => run(api.post(`/org/users/${u.id}/reactivate`), `${u.email} reactivated.`)}
                    >
                      Reactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td className="p-4 text-slate-400" colSpan={5}>
                  No logins yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <form onSubmit={createHr} className="bg-white rounded-lg shadow p-4 space-y-3">
        <h2 className="font-semibold">Create an HR login</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <input
            className="border rounded px-2 py-1 text-sm"
            placeholder="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
          <input
            type="email"
            className="border rounded px-2 py-1 text-sm"
            placeholder="Email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
          <input
            type="password"
            className="border rounded px-2 py-1 text-sm"
            placeholder="Temporary password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.require_password_change}
            onChange={(e) => setForm({ ...form, require_password_change: e.target.checked })}
          />
          Require a password change on first sign-in
          <span className="text-xs text-slate-400">— uncheck for a shared demo login</span>
        </label>
        <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Create HR login</button>
      </form>

      <p className="text-xs text-slate-400">
        An Admin cannot change their own role or deactivate their own login, and the last active Admin is protected —
        otherwise the company could be locked out of its own system.
      </p>
    </div>
  );
}
