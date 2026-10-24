import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";

export default function MyLeave() {
  const [balance, setBalance] = useState<any[]>([]);
  const [mine, setMine] = useState<any[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  const [smartText, setSmartText] = useState("");
  const [suggestion, setSuggestion] = useState<any>(null);
  const [smartLoading, setSmartLoading] = useState(false);

  const [form, setForm] = useState({ leave_type_id: "", start_date: "", end_date: "", reason: "" });

  function load() {
    api.get("/leave/balance").then((r) => setBalance(r.data));
    api.get("/leave/mine").then((r) => setMine(r.data));
    api.get("/org/leave-types").then((r) => setLeaveTypes(r.data)).catch(() => {});
  }
  useEffect(load, []);

  async function askSmart() {
    setSmartLoading(true);
    setMsg("");
    try {
      const res = await api.post("/leave/smart", { text: smartText });
      setSuggestion(res.data);
      if (res.data.leave_type_id) {
        setForm({
          leave_type_id: String(res.data.leave_type_id),
          start_date: res.data.start_date || "",
          end_date: res.data.end_date || "",
          reason: res.data.reason || smartText,
        });
      }
    } catch (err) {
      setMsg(apiErrorMessage(err));
    } finally {
      setSmartLoading(false);
    }
  }

  async function apply(e: FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await api.post("/leave/apply", {
        leave_type_id: Number(form.leave_type_id),
        start_date: form.start_date,
        end_date: form.end_date,
        reason: form.reason,
      });
      setMsg("Leave request submitted");
      setForm({ leave_type_id: "", start_date: "", end_date: "", reason: "" });
      setSuggestion(null);
      setSmartText("");
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function cancel(id: number) {
    await api.post(`/leave/${id}/cancel`);
    load();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">My leave</h1>
      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2">{msg}</div>}

      <div className="bg-white rounded-lg shadow p-4 space-y-2">
        <h2 className="font-semibold">Smart leave</h2>
        <p className="text-xs text-slate-500">Type your request in plain words, e.g. "Need next Monday and Tuesday off for a wedding".</p>
        <div className="flex gap-2">
          <input className="flex-1 border rounded px-2 py-1 text-sm" value={smartText} onChange={(e) => setSmartText(e.target.value)} />
          <button className="bg-brand text-white rounded px-4 text-sm" onClick={askSmart} disabled={smartLoading || !smartText}>
            {smartLoading ? "Thinking..." : "Suggest"}
          </button>
        </div>
      </div>

      <form onSubmit={apply} className="bg-white rounded-lg shadow p-4 grid grid-cols-2 gap-3">
        <h2 className="font-semibold col-span-2">{suggestion ? "Confirm leave request" : "Apply for leave"}</h2>
        <select className="border rounded px-2 py-1 text-sm" value={form.leave_type_id} onChange={(e) => setForm({ ...form, leave_type_id: e.target.value })} required>
          <option value="">Leave type</option>
          {leaveTypes.map((lt) => (
            <option key={lt.id} value={lt.id}>
              {lt.name}
            </option>
          ))}
        </select>
        <div />
        <label className="text-sm">
          Start date
          <input type="date" className="block w-full border rounded px-2 py-1" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required />
        </label>
        <label className="text-sm">
          End date
          <input type="date" className="block w-full border rounded px-2 py-1" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} required />
        </label>
        <input className="col-span-2 border rounded px-2 py-1 text-sm" placeholder="Reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} required />
        <button className="col-span-2 bg-brand text-white rounded px-4 py-1.5 text-sm">Submit</button>
      </form>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Balance ({new Date().getFullYear()})</h2>
        <ul className="text-sm space-y-1">
          {balance.map((b) => (
            <li key={b.leave_type_id}>
              {b.leave_type_name}: {b.remaining === null ? "unlimited" : `${b.remaining} of ${b.quota} left`}
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">My requests</h2>
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Dates</th>
              <th className="p-2">Days</th>
              <th className="p-2">Status</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {mine.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="p-2">
                  {r.start_date} → {r.end_date}
                </td>
                <td className="p-2">{r.days}</td>
                <td className="p-2 capitalize">{r.status}</td>
                <td className="p-2">
                  {r.status === "pending" && (
                    <button className="text-red-700" onClick={() => cancel(r.id)}>
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
