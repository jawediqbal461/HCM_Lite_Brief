import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";
import CameraCheckIn from "../../components/CameraCheckIn";

export default function MyAttendance() {
  const [today, setToday] = useState<any>(null);
  const [calendar, setCalendar] = useState<any[]>([]);
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [msg, setMsg] = useState("");
  const [corrDate, setCorrDate] = useState("");
  const [corrReason, setCorrReason] = useState("");

  function load(forMonth = month) {
    const [y, m] = forMonth.split("-").map(Number);
    const start = `${forMonth}-01`;
    const end = new Date(y, m, 0).toISOString().slice(0, 10);
    api.get("/attendance/calendar", { params: { start, end } }).then((r) => setCalendar(r.data));

    // "Today" is read separately so it stays right even when browsing an old month.
    const todayStr = new Date().toISOString().slice(0, 10);
    api
      .get("/attendance/calendar", { params: { start: todayStr, end: todayStr } })
      .then((r) => setToday(r.data[0] || null));
  }
  useEffect(() => load(month), [month]);

  async function checkIn() {
    setMsg("");
    try {
      await api.post("/attendance/check-in", { source: "web" });
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function checkOut() {
    setMsg("");
    try {
      await api.post("/attendance/check-out");
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function requestCorrection(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/attendance/corrections", { date: corrDate, reason: corrReason });
      setMsg("Correction requested");
      setCorrDate("");
      setCorrReason("");
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">My attendance</h1>
      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2">{msg}</div>}

      <div className="bg-white rounded-lg shadow p-4 flex items-center gap-4">
        <div className="text-sm">
          Today: <span className="font-medium capitalize">{today ? today.status.replace("_", " ") : "not checked in"}</span>
        </div>
        <button className="bg-brand text-white rounded px-4 py-1.5 text-sm" onClick={checkIn} disabled={!!today?.check_in_time}>
          Check in
        </button>
        <button className="bg-slate-700 text-white rounded px-4 py-1.5 text-sm" onClick={checkOut} disabled={!today?.check_in_time || !!today?.check_out_time}>
          Check out
        </button>
      </div>

      <CameraCheckIn onCheckedIn={load} />

      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
          <h2 className="font-semibold">My attendance</h2>
          <label className="text-sm">
            Month{" "}
            <input type="month" className="border rounded px-2 py-1" value={month} onChange={(e) => setMonth(e.target.value)} />
          </label>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Date</th>
              <th className="p-2">Check in</th>
              <th className="p-2">Check out</th>
              <th className="p-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {calendar.map((c) => (
              <tr key={c.id} className="border-t">
                <td className="p-2">{c.date}</td>
                <td className="p-2">{c.check_in_time ? new Date(c.check_in_time).toLocaleTimeString() : "-"}</td>
                <td className="p-2">{c.check_out_time ? new Date(c.check_out_time).toLocaleTimeString() : "-"}</td>
                <td className="p-2 capitalize">{c.status.replace("_", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-2">Request a correction</h2>
        <form onSubmit={requestCorrection} className="flex gap-2 items-end">
          <label className="text-sm">
            Date
            <input type="date" className="block border rounded px-2 py-1" value={corrDate} onChange={(e) => setCorrDate(e.target.value)} required />
          </label>
          <label className="text-sm flex-1">
            Reason
            <input className="block w-full border rounded px-2 py-1" value={corrReason} onChange={(e) => setCorrReason(e.target.value)} required />
          </label>
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Request</button>
        </form>
      </div>
    </div>
  );
}
