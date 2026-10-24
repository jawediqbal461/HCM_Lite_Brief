import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [checkingSetup, setCheckingSetup] = useState(true);
  const { login, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/auth/first-run-status").then((res) => {
      if (res.data.first_run) navigate("/first-run", { replace: true });
      setCheckingSetup(false);
    });
  }, [navigate]);

  useEffect(() => {
    if (user) {
      navigate(user.mustChangePassword ? "/change-password" : `/${user.role}`, { replace: true });
    }
  }, [user, navigate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  if (checkingSetup) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <form onSubmit={onSubmit} className="bg-white p-8 rounded-lg shadow w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold text-brand-dark">HCM Lite — Sign in</h1>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        <div>
          <label className="block text-sm mb-1">Email</label>
          <input className="w-full border rounded px-3 py-2" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="block text-sm mb-1">Password</label>
          <input
            type="password"
            className="w-full border rounded px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button className="w-full bg-brand text-white rounded py-2 font-medium" type="submit">
          Sign in
        </button>
      </form>
    </div>
  );
}
