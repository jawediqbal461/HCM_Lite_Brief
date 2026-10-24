import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ChangePassword() {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const { user, refreshMe } = useAuth();
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/change-password", { old_password: oldPassword, new_password: newPassword });
      setDone(true);
      await refreshMe();
      setTimeout(() => navigate(`/${user?.role || ""}`), 800);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <form onSubmit={onSubmit} className="bg-white p-8 rounded-lg shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold text-brand-dark">Change your password</h1>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        {done && <div className="text-green-600 text-sm">Password changed, redirecting…</div>}
        <div>
          <label className="block text-sm mb-1">Current / temporary password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm mb-1">New password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={8}
            required
          />
        </div>
        <button className="w-full bg-brand text-white rounded py-2 font-medium" type="submit">
          Update password
        </button>
      </form>
    </div>
  );
}
