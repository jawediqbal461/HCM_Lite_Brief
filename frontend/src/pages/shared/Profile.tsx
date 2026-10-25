import { FormEvent, useEffect, useState } from "react";
import api, { apiErrorMessage } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export default function Profile() {
  const { user } = useAuth();
  const [account, setAccount] = useState<any>(null);
  const [employee, setEmployee] = useState<any>(null);

  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [detailsMsg, setDetailsMsg] = useState("");

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordError, setPasswordError] = useState("");

  function load() {
    api.get("/auth/me").then((r) => setAccount(r.data));
    api
      .get("/employees/me")
      .then((r) => {
        setEmployee(r.data);
        setPhone(r.data.phone || "");
        setAddress(r.data.address || "");
      })
      // Admin and HR logins have no employee record; that is expected.
      .catch(() => setEmployee(null));
  }
  useEffect(load, []);

  async function saveDetails(e: FormEvent) {
    e.preventDefault();
    setDetailsMsg("");
    try {
      await api.patch("/employees/me", { phone, address });
      setDetailsMsg("Saved.");
      load();
    } catch (err) {
      setDetailsMsg(apiErrorMessage(err));
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setPasswordMsg("");
    setPasswordError("");

    if (newPassword !== confirmPassword) {
      setPasswordError("The two new passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("Use at least 8 characters.");
      return;
    }

    try {
      await api.post("/auth/change-password", { old_password: oldPassword, new_password: newPassword });
      setPasswordMsg("Password changed. It applies the next time you sign in.");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      load();
    } catch (err) {
      setPasswordError(apiErrorMessage(err));
    }
  }

  if (!account) return <div>Loading...</div>;

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-brand-dark">My profile</h1>

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-3">Account</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-slate-500">Name:</span> {account.full_name || "—"}
          </div>
          <div>
            <span className="text-slate-500">Email:</span> {account.email}
          </div>
          <div>
            <span className="text-slate-500">Role:</span> <span className="capitalize">{account.role}</span>
          </div>
          {employee && (
            <div>
              <span className="text-slate-500">Employee code:</span> {employee.code}
            </div>
          )}
        </div>
        {!employee && (
          <p className="text-xs text-slate-400 mt-3">
            This login has no employee record of its own, which is normal for Admin and HR accounts.
          </p>
        )}
      </div>

      {employee && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold mb-1">My details</h2>
          <p className="text-xs text-slate-400 mb-3">
            You can update your phone and address. Job details and salary are maintained by HR.
          </p>
          {detailsMsg && <div className="text-sm bg-brand/10 text-brand-dark rounded px-3 py-2 mb-3">{detailsMsg}</div>}
          <form onSubmit={saveDetails} className="space-y-3">
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
          <div className="grid grid-cols-2 gap-2 text-sm mt-4 pt-4 border-t text-slate-600">
            <div>
              <span className="text-slate-500">Joined:</span> {employee.date_of_joining}
            </div>
            <div>
              <span className="text-slate-500">Status:</span> <span className="capitalize">{employee.status}</span>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="font-semibold mb-1">Change password</h2>
        <p className="text-xs text-slate-400 mb-3">
          {user?.mustChangePassword
            ? "You are still using a temporary password. Set your own below."
            : "Choose something long — length matters more than symbols."}
        </p>
        {passwordMsg && <div className="text-sm bg-green-50 text-green-800 rounded px-3 py-2 mb-3">{passwordMsg}</div>}
        {passwordError && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2 mb-3">{passwordError}</div>}
        <form onSubmit={changePassword} className="space-y-3">
          <label className="block text-sm">
            Current password
            <input
              type="password"
              className="w-full border rounded px-2 py-1"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm">
            New password
            <input
              type="password"
              className="w-full border rounded px-2 py-1"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          <label className="block text-sm">
            Confirm new password
            <input
              type="password"
              className="w-full border rounded px-2 py-1"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Update password</button>
        </form>
      </div>
    </div>
  );
}
