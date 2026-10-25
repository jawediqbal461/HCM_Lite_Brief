import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { apiErrorMessage } from "../../api/client";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <h2 className="font-semibold text-brand-dark">{title}</h2>
      {children}
    </div>
  );
}

export default function CompanySettings() {
  const [settings, setSettings] = useState<any>(null);
  const [departments, setDepartments] = useState<any[]>([]);
  const [designations, setDesignations] = useState<any[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<any[]>([]);
  const [holidays, setHolidays] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  const [deptName, setDeptName] = useState("");
  const [desigName, setDesigName] = useState("");
  const [ltName, setLtName] = useState("");
  const [ltQuota, setLtQuota] = useState("");
  const [holDate, setHolDate] = useState("");
  const [holName, setHolName] = useState("");


  function loadAll() {
    api.get("/org/settings").then((r) => setSettings(r.data));
    api.get("/org/departments").then((r) => setDepartments(r.data));
    api.get("/org/designations").then((r) => setDesignations(r.data));
    api.get("/org/leave-types").then((r) => setLeaveTypes(r.data));
    api.get("/org/holidays").then((r) => setHolidays(r.data));
  }

  useEffect(loadAll, []);

  async function saveSettings(e: FormEvent) {
    e.preventDefault();
    try {
      await api.put("/org/settings", {
        timezone: settings.timezone,
        office_start_time: settings.office_start_time,
        grace_minutes: Number(settings.grace_minutes),
        half_day_hours: Number(settings.half_day_hours),
        weekend_days: settings.weekend_days,
        office_lat: settings.office_lat ? Number(settings.office_lat) : null,
        office_lng: settings.office_lng ? Number(settings.office_lng) : null,
        office_radius_m: Number(settings.office_radius_m),
      });
      setMsg("Settings saved");
      loadAll();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  async function addDept(e: FormEvent) {
    e.preventDefault();
    await api.post("/org/departments", { name: deptName });
    setDeptName("");
    loadAll();
  }
  async function addDesig(e: FormEvent) {
    e.preventDefault();
    await api.post("/org/designations", { name: desigName });
    setDesigName("");
    loadAll();
  }
  async function addLeaveType(e: FormEvent) {
    e.preventDefault();
    await api.post("/org/leave-types", { name: ltName, annual_quota: ltQuota ? Number(ltQuota) : null });
    setLtName("");
    setLtQuota("");
    loadAll();
  }
  async function addHoliday(e: FormEvent) {
    e.preventDefault();
    await api.post("/org/holidays", { date: holDate, name: holName });
    setHolDate("");
    setHolName("");
    loadAll();
  }

  if (!settings) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">Company setup</h1>
      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2">{msg}</div>}

      <Section title="Office rules">
        <form onSubmit={saveSettings} className="grid grid-cols-2 gap-3">
          <label className="text-sm col-span-2">
            Timezone (attendance dates and the late rule use this)
            <input
              className="w-full border rounded px-2 py-1"
              placeholder="e.g. Asia/Karachi"
              value={settings.timezone}
              onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Office start time
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.office_start_time}
              onChange={(e) => setSettings({ ...settings, office_start_time: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Grace minutes
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.grace_minutes}
              onChange={(e) => setSettings({ ...settings, grace_minutes: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Half day under (hours)
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.half_day_hours}
              onChange={(e) => setSettings({ ...settings, half_day_hours: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Weekend days (0=Mon..6=Sun, comma separated)
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.weekend_days}
              onChange={(e) => setSettings({ ...settings, weekend_days: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Office latitude
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.office_lat ?? ""}
              onChange={(e) => setSettings({ ...settings, office_lat: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Office longitude
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.office_lng ?? ""}
              onChange={(e) => setSettings({ ...settings, office_lng: e.target.value })}
            />
          </label>
          <label className="text-sm">
            Radius (meters)
            <input
              className="w-full border rounded px-2 py-1"
              value={settings.office_radius_m}
              onChange={(e) => setSettings({ ...settings, office_radius_m: e.target.value })}
            />
          </label>
          <div className="col-span-2 flex items-center gap-3">
            <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Save</button>
            <button
              type="button"
              className="text-sm text-brand underline"
              onClick={() => {
                if (!window.isSecureContext) {
                  setMsg("Location needs HTTPS. Open this site over https:// to use it.");
                  return;
                }
                setMsg("Getting your location…");
                navigator.geolocation.getCurrentPosition(
                  (pos) => {
                    setSettings({
                      ...settings,
                      office_lat: pos.coords.latitude,
                      office_lng: pos.coords.longitude,
                    });
                    setMsg(`Filled from your location (±${Math.round(pos.coords.accuracy)} m). Press Save to apply.`);
                  },
                  () => setMsg("Could not get your location. Allow location access and try again."),
                  { enableHighAccuracy: true, timeout: 15000 },
                );
              }}
            >
              Use my current location
            </button>
            <span className="text-xs text-slate-400">Sit at the office and click this to set the check-in area.</span>
          </div>
        </form>
      </Section>

      <div className="grid grid-cols-2 gap-6">
        <Section title="Departments">
          <ul className="text-sm space-y-1">
            {departments.map((d) => (
              <li key={d.id}>{d.name}</li>
            ))}
          </ul>
          <form onSubmit={addDept} className="flex gap-2">
            <input className="flex-1 border rounded px-2 py-1 text-sm" placeholder="New department" value={deptName} onChange={(e) => setDeptName(e.target.value)} required />
            <button className="bg-brand text-white rounded px-3 text-sm">Add</button>
          </form>
        </Section>

        <Section title="Designations">
          <ul className="text-sm space-y-1">
            {designations.map((d) => (
              <li key={d.id}>{d.name}</li>
            ))}
          </ul>
          <form onSubmit={addDesig} className="flex gap-2">
            <input className="flex-1 border rounded px-2 py-1 text-sm" placeholder="New designation" value={desigName} onChange={(e) => setDesigName(e.target.value)} required />
            <button className="bg-brand text-white rounded px-3 text-sm">Add</button>
          </form>
        </Section>

        <Section title="Leave types & quotas">
          <ul className="text-sm space-y-1">
            {leaveTypes.map((lt) => (
              <li key={lt.id}>
                {lt.name} — {lt.annual_quota ?? "unlimited"} days/yr
              </li>
            ))}
          </ul>
          <form onSubmit={addLeaveType} className="flex gap-2">
            <input className="flex-1 border rounded px-2 py-1 text-sm" placeholder="Name" value={ltName} onChange={(e) => setLtName(e.target.value)} required />
            <input className="w-24 border rounded px-2 py-1 text-sm" placeholder="Quota" value={ltQuota} onChange={(e) => setLtQuota(e.target.value)} />
            <button className="bg-brand text-white rounded px-3 text-sm">Add</button>
          </form>
        </Section>

        <Section title="Public holidays">
          <ul className="text-sm space-y-1 max-h-32 overflow-y-auto">
            {holidays.map((h) => (
              <li key={h.id}>
                {h.date} — {h.name}
              </li>
            ))}
          </ul>
          <form onSubmit={addHoliday} className="flex gap-2">
            <input type="date" className="border rounded px-2 py-1 text-sm" value={holDate} onChange={(e) => setHolDate(e.target.value)} required />
            <input className="flex-1 border rounded px-2 py-1 text-sm" placeholder="Name" value={holName} onChange={(e) => setHolName(e.target.value)} required />
            <button className="bg-brand text-white rounded px-3 text-sm">Add</button>
          </form>
        </Section>
      </div>

      <Section title="Logins">
        <p className="text-sm text-slate-500">
          HR logins, role changes, password resets and deactivation live on the{" "}
          <Link to="/admin/users" className="text-brand underline">
            Users &amp; access
          </Link>{" "}
          page.
        </p>
      </Section>
    </div>
  );
}
