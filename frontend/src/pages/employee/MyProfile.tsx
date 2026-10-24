import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";

export default function MyProfile() {
  const [profile, setProfile] = useState<any>(null);
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [msg, setMsg] = useState("");

  function load() {
    api.get("/employees/me").then((r) => {
      setProfile(r.data);
      setPhone(r.data.phone || "");
      setAddress(r.data.address || "");
    });
  }
  useEffect(load, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    try {
      await api.patch("/employees/me", { phone, address });
      setMsg("Profile updated");
      load();
    } catch (err) {
      setMsg(apiErrorMessage(err));
    }
  }

  if (!profile) return <div>Loading...</div>;

  return (
    <div className="max-w-lg space-y-4">
      <h1 className="text-2xl font-bold text-brand-dark">My profile</h1>
      {msg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2">{msg}</div>}
      <div className="bg-white rounded-lg shadow p-4 space-y-1 text-sm">
        <div>
          <span className="text-slate-500">Code:</span> {profile.code}
        </div>
        <div>
          <span className="text-slate-500">Name:</span> {profile.full_name}
        </div>
        <div>
          <span className="text-slate-500">Email:</span> {profile.email}
        </div>
        <div>
          <span className="text-slate-500">Joined:</span> {profile.date_of_joining}
        </div>
      </div>
      <form onSubmit={save} className="bg-white rounded-lg shadow p-4 space-y-3">
        <label className="block text-sm">
          Phone
          <input className="w-full border rounded px-2 py-1" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
        <label className="block text-sm">
          Address
          <input className="w-full border rounded px-2 py-1" value={address} onChange={(e) => setAddress(e.target.value)} />
        </label>
        <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Save</button>
      </form>
    </div>
  );
}
