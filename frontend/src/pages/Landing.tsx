import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const MODULES = [
  {
    title: "Attendance",
    body: "Web check-in and check-out with the server stamping the time. Late, half-day and missing-checkout are decided by your own office rules, not guesswork.",
  },
  {
    title: "Camera check-in",
    body: "Optional face-detected check-in that is only accepted inside the office geofence. The server measures the distance itself, so it cannot be faked from the browser.",
  },
  {
    title: "Leave",
    body: "Apply in working days only — weekends and public holidays are skipped. Overlapping requests and over-balance requests are rejected before they reach HR.",
  },
  {
    title: "Payroll",
    body: "Monthly runs with allowances, absence and unpaid-leave deductions, tax slabs and proration for joiners and leavers. Admin finalizes, and a finalized month locks.",
  },
  {
    title: "Dashboards",
    body: "Attendance rate, absenteeism, leave utilization, payroll cost and headcount — computed on the server from real records, filterable by date range and department.",
  },
  {
    title: "AI assistant",
    body: "Ask questions in plain words and get answers from the same services the dashboards use, so the numbers always agree. It only ever sees what your role is allowed to see.",
  },
  {
    title: "Employee 360",
    body: "One page per employee: profile, attendance history, every leave request and all payslips, with PDF download.",
  },
  {
    title: "Audit log",
    body: "Every create, update, approval and payroll finalization is recorded with who did it and what changed, before and after.",
  },
];

const ROLES = [
  { role: "Admin", body: "Company setup, office rules and location, departments and leave types, HR logins, payroll finalization, the audit log, and company-wide analytics." },
  { role: "HR", body: "Register employees, salary structures, the daily attendance board, leave approvals, attendance corrections and the monthly payroll draft." },
  { role: "Employee", body: "Check in and out, own attendance calendar, leave with live balance, payslip downloads, and an assistant limited to their own data." },
];

export default function Landing() {
  const [firstRun, setFirstRun] = useState<boolean | null>(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate(`/${user.role}`, { replace: true });
      return;
    }
    api
      .get("/auth/first-run-status")
      .then((r) => setFirstRun(r.data.first_run))
      .catch(() => setFirstRun(null));
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-white text-slate-800">
      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b">
        <div className="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
          <div className="font-bold text-brand-dark text-lg">HCM Lite</div>
          <nav className="flex items-center gap-2">
            <Link to="/login" className="px-4 py-2 text-sm rounded border hover:bg-slate-50">
              Sign in
            </Link>
            {firstRun && (
              <Link to="/first-run" className="px-4 py-2 text-sm rounded bg-brand text-white hover:opacity-90">
                Set up your company
              </Link>
            )}
          </nav>
        </div>
      </header>

      <section className="bg-brand-dark text-white">
        <div className="max-w-6xl mx-auto px-5 py-16 md:py-24">
          <p className="text-brand font-semibold tracking-wide text-sm">AI-ASSISTED HUMAN CAPITAL MANAGEMENT</p>
          <h1 className="text-3xl md:text-5xl font-bold mt-3 max-w-3xl leading-tight">
            Attendance, leave and payroll that actually agree with each other.
          </h1>
          <p className="mt-5 text-white/70 max-w-2xl text-lg">
            One system for Admin, HR and Employees. Every number on a dashboard comes from a real record someone
            created in the app — and the AI assistant answers from those same records, with your own permissions.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/login" className="px-6 py-3 rounded bg-brand text-white font-medium hover:opacity-90">
              Sign in
            </Link>
            {firstRun && (
              <Link to="/first-run" className="px-6 py-3 rounded bg-white text-brand-dark font-medium hover:bg-slate-100">
                Set up your company
              </Link>
            )}
          </div>
          {firstRun === false && (
            <p className="mt-4 text-sm text-white/50">
              This company is already set up. New employees get their login from HR.
            </p>
          )}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-5 py-16">
        <h2 className="text-2xl font-bold text-brand-dark">What it does</h2>
        <p className="text-slate-500 mt-1">Nine modules, built so the rules live in one place.</p>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5 mt-8">
          {MODULES.map((m) => (
            <div key={m.title} className="border rounded-lg p-5 hover:shadow-sm transition-shadow">
              <h3 className="font-semibold text-brand-dark">{m.title}</h3>
              <p className="text-sm text-slate-600 mt-2 leading-relaxed">{m.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-slate-50 border-y">
        <div className="max-w-6xl mx-auto px-5 py-16">
          <h2 className="text-2xl font-bold text-brand-dark">Three roles, enforced on the server</h2>
          <p className="text-slate-500 mt-1">
            Hiding a button is not security, so every request is checked again on the backend — including the ones the
            AI assistant makes.
          </p>
          <div className="grid md:grid-cols-3 gap-5 mt-8">
            {ROLES.map((r) => (
              <div key={r.role} className="bg-white border rounded-lg p-5">
                <h3 className="font-semibold text-brand-dark">{r.role}</h3>
                <p className="text-sm text-slate-600 mt-2 leading-relaxed">{r.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="max-w-6xl mx-auto px-5 py-10 text-sm text-slate-500 flex flex-wrap gap-4 justify-between">
        <span>HCM Lite — Saylani Hackathon</span>
        <Link to="/login" className="text-brand underline">
          Sign in
        </Link>
      </footer>
    </div>
  );
}
