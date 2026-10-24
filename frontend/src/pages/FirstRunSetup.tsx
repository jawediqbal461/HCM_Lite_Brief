import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function FirstRunSetup() {
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { refreshMe } = useAuth();
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/auth/first-run-setup", {
        company_name: companyName,
        admin_email: email,
        admin_password: password,
      });
      localStorage.setItem("hcm_token", res.data.access_token);
      await refreshMe();
      navigate("/admin", { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <form onSubmit={onSubmit} className="bg-white p-8 rounded-lg shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold text-brand-dark">Welcome — set up your company</h1>
        <p className="text-sm text-slate-500">This runs once. It creates your company and the first Admin account.</p>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        <div>
          <label className="block text-sm mb-1">Company name</label>
          <input className="w-full border rounded px-3 py-2" value={companyName} onChange={(e) => setCompanyName(e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm mb-1">Admin email</label>
          <input
            type="email"
            className="w-full border rounded px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm mb-1">Admin password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </div>
        <button className="w-full bg-brand text-white rounded py-2 font-medium" type="submit">
          Create company
        </button>
      </form>
    </div>
  );
}
