import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";
import BrowserFrame from "../components/BrowserFrame";

const NAV_LINKS = [
  { href: "#company-setup", label: "Get started" },
  { href: "#admin", label: "For Admin" },
  { href: "#hr", label: "For HR" },
  { href: "#employee", label: "For Employees" },
  { href: "#reports", label: "Reports" },
];

const MODULES = [
  { title: "Attendance", body: "Web check-in/out with the server stamping the time. Late, half-day and absent follow your own office hours and grace period." },
  { title: "Leave", body: "Applied in working days only — weekends and holidays are skipped. Overlaps and over-balance requests are refused before HR sees them." },
  { title: "Payroll", body: "Allowances, absence and unpaid-leave deductions, the late-penalty rule, and tax slabs. Admin finalizes, and a finalized month locks." },
  { title: "Dashboards", body: "Attendance rate, absenteeism, leave utilization, payroll cost and headcount — computed on the server, filterable by date range and department." },
  { title: "Reports", body: "Eight period reports with totals, each exportable to CSV — registers, late arrivals, headcount and attrition, and personal statements." },
  { title: "Employee 360", body: "One page per employee: profile, attendance history, every leave request and all payslips, with PDF download." },
  { title: "Insights", body: "Attrition risk and absence anomalies, each with the reasons behind the score — signals to look into, not verdicts." },
  { title: "Audit log", body: "Every create, update, approval and payroll finalization is recorded with who did it and what changed." },
];

const HIGHLIGHTS = [
  {
    tag: "Face + location",
    title: "Camera attendance that cannot be faked from the sofa",
    body: "Check in with the camera and it is accepted only when exactly one face is in frame and the device is inside the office area. Face detection runs on the device itself, and no photo is ever stored — only the result.",
    points: [
      "Exactly one face required: zero or several are both refused",
      "The server recalculates the distance to the office with the Haversine formula",
      "A GPS fix vaguer than 100 m is rejected as too weak to prove presence",
      "Every rule is re-checked on the server, so editing the browser proves nothing",
    ],
  },
  {
    tag: "AI assistant",
    title: "Ask in plain words, get answers from the real records",
    body: "The assistant calls the same services the dashboards use, so its answers and the charts can never disagree. It runs with the permissions of whoever is asking.",
    points: [
      "\"What is this month's attendance rate?\" — the same number the dashboard shows",
      "\"How many sick leaves do I have left?\" — the employee's own balance, nobody else's",
      "Type a sentence like \"next Monday and Tuesday off for a wedding\" and get a filled-in leave form",
      "Ask a colleague's salary and it declines — no tool in the system can even fetch it for them",
    ],
  },
];

function RoleSection({
  id,
  eyebrow,
  title,
  body,
  points,
  image,
  alt,
  caption,
  reverse,
}: {
  id: string;
  eyebrow: string;
  title: string;
  body: string;
  points: string[];
  image: string;
  alt: string;
  caption: string;
  reverse?: boolean;
}) {
  return (
    <section id={id} className="max-w-6xl mx-auto px-5 py-16 scroll-mt-20">
      <div className={`grid md:grid-cols-2 gap-10 items-center ${reverse ? "md:[&>*:first-child]:order-2" : ""}`}>
        <div className={reverse ? "md:order-2" : ""}>
          <BrowserFrame src={image} alt={alt} caption={caption} />
        </div>
        <div>
          <span className="text-xs font-semibold tracking-wide text-brand uppercase">{eyebrow}</span>
          <h2 className="text-2xl md:text-3xl font-bold text-brand-dark mt-2">{title}</h2>
          <p className="text-slate-600 mt-3 leading-relaxed">{body}</p>
          <ul className="mt-5 space-y-2.5">
            {points.map((p) => (
              <li key={p} className="flex gap-2 text-sm text-slate-700">
                <span className="text-brand font-bold shrink-0">✓</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

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
      {/* ---------- top nav ---------- */}
      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b">
        <div className="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
          <div className="font-bold text-brand-dark text-lg">HCM Lite</div>
          <nav className="hidden md:flex items-center gap-6">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} className="text-sm text-slate-600 hover:text-brand-dark">
                {l.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login" className="px-4 py-2 text-sm rounded border hover:bg-slate-50">
              Sign in
            </Link>
            {firstRun && (
              <Link to="/first-run" className="px-4 py-2 text-sm rounded bg-brand text-white hover:opacity-90">
                Set up your company
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* ---------- hero ---------- */}
      <section className="bg-brand-dark text-white">
        <div className="max-w-6xl mx-auto px-5 py-16 md:py-20 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <p className="text-brand font-semibold tracking-wide text-sm">AI-ASSISTED HUMAN CAPITAL MANAGEMENT</p>
            <h1 className="text-3xl md:text-5xl font-bold mt-3 leading-tight">
              Attendance, leave and payroll that actually agree with each other.
            </h1>
            <p className="mt-5 text-white/70 text-lg">
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
              <p className="mt-4 text-sm text-white/50">This company is already set up. New employees get their login from HR.</p>
            )}
          </div>
          <div className="hidden md:block">
            <BrowserFrame src="/screenshots/admin-dashboard.jpg" alt="HCM Lite company dashboard with charts and KPIs" />
          </div>
        </div>
      </section>

      {/* ---------- modules grid ---------- */}
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

      {/* ---------- company creation ---------- */}
      <section id="company-setup" className="bg-slate-50 border-y scroll-mt-20">
        <div className="max-w-6xl mx-auto px-5 py-16 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span className="text-xs font-semibold tracking-wide text-brand uppercase">Getting started</span>
            <h2 className="text-2xl md:text-3xl font-bold text-brand-dark mt-2">From an empty install to a working company in minutes</h2>
            <p className="text-slate-600 mt-3 leading-relaxed">
              There is no pre-loaded or dummy data. The first screen anyone sees creates the company and the first
              Admin account — everything after that is built from what people actually do in the app.
            </p>
            <ol className="mt-5 space-y-3 text-sm text-slate-700">
              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-brand text-white text-xs flex items-center justify-center shrink-0">1</span>
                <span><strong>Admin</strong> sets up the company — name, office hours, location and rules.</span>
              </li>
              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-brand text-white text-xs flex items-center justify-center shrink-0">2</span>
                <span><strong>HR</strong> registers employees, which creates each one's login automatically.</span>
              </li>
              <li className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-brand text-white text-xs flex items-center justify-center shrink-0">3</span>
                <span><strong>Everyone</strong> signs in, changes their temporary password, and starts using the app.</span>
              </li>
            </ol>
          </div>
          <BrowserFrame src="/screenshots/company-setup.jpg" alt="First-run company setup screen" caption="The actual first screen of a new install — no demo data, no shortcuts." />
        </div>
      </section>

      {/* ---------- role sections ---------- */}
      <RoleSection
        id="admin"
        eyebrow="For Admin"
        title="Company-wide visibility, with the controls that matter kept out of reach of everyone else"
        body="Admin owns the rules — office hours, departments, leave types, who can log in — and is the only role that can finalize payroll or lock an attendance month."
        points={[
          "Create, deactivate and reset logins for HR and employees",
          "Promote or demote a role, with guards so the company can never lock itself out",
          "Finalize the monthly payroll prepared by HR — only Admin can lock it",
          "Company-wide dashboard, insights and the full audit log",
        ]}
        image="/screenshots/users-access.jpg"
        alt="Users and access management screen"
        caption="Every login in the system, with role changes and credential resets in one place."
      />

      <RoleSection
        id="hr"
        eyebrow="For HR"
        title="The daily work of running people operations, without leaving the browser"
        body="Register employees, review attendance, approve leave and run payroll — all filtered, paged and exportable, so the list in front of you is never the whole database."
        points={[
          "Register an employee and edit their details or salary at any time",
          "Daily attendance board, with corrections approved or rejected in a click",
          "Leave approvals with a comment, and a monthly payroll draft ready for Admin",
          "CSV import with a dry run that reports the exact row, field and reason for every error",
        ]}
        image="/screenshots/hr-dashboard.jpg"
        alt="HR dashboard with attendance trend and leave charts"
        caption="Headcount, late-comers, attendance trend and leave by type — filtered by date and department."
        reverse
      />

      <RoleSection
        id="employee"
        eyebrow="For Employees"
        title="Self-service that does not need a phone call to HR"
        body="Check in, see where leave balance actually stands, and download a payslip the moment it exists — without waiting on anyone."
        points={[
          "Check in and out, including the optional face-and-location camera check-in",
          "Apply for leave in plain words, or the normal form — balance updates live",
          "Download any payslip the moment payroll is finalized",
          "An AI assistant scoped to their own data, and nobody else's",
        ]}
        image="/screenshots/employee-dashboard.jpg"
        alt="Employee personal dashboard with check-in and leave balance"
        caption="A real employee's dashboard: hours this week, leave balance, last payslip."
      />

      {/* ---------- everyday operations strip ---------- */}
      <section className="bg-slate-50 border-y">
        <div className="max-w-6xl mx-auto px-5 py-16">
          <h2 className="text-2xl font-bold text-brand-dark">The screens people actually live in</h2>
          <p className="text-slate-500 mt-1">Filtered, paged, and exportable — not a dump of every row in the database.</p>
          <div className="grid md:grid-cols-3 gap-6 mt-8">
            <BrowserFrame src="/screenshots/attendance-board.jpg" alt="Daily attendance board" caption="Daily attendance board — everyone, not just who checked in." />
            <BrowserFrame src="/screenshots/employees-directory.jpg" alt="Employee directory" caption="Employee directory with search, filters and CSV export." />
            <BrowserFrame src="/screenshots/payroll.jpg" alt="Finalized payroll run" caption="A finalized payroll run, with the late-penalty line shown openly." />
          </div>
        </div>
      </section>

      {/* ---------- reports & insights ---------- */}
      <section id="reports" className="max-w-6xl mx-auto px-5 py-16 scroll-mt-20">
        <h2 className="text-2xl font-bold text-brand-dark">Reports and insights, from the same records</h2>
        <p className="text-slate-500 mt-1">Eight reports with totals and CSV export, plus attrition risk and absence anomalies — every score explains itself.</p>
        <div className="grid md:grid-cols-2 gap-6 mt-8">
          <BrowserFrame src="/screenshots/reports.jpg" alt="Attendance register report" caption="One of eight reports — a register, a month, or a year, picked per report." />
          <BrowserFrame src="/screenshots/insights.jpg" alt="Attrition risk insights" caption="Attrition risk with the factors behind each score, not a bare number." />
        </div>
      </section>

      {/* ---------- camera + AI highlights ---------- */}
      <section className="bg-slate-50 border-y">
        <div className="max-w-6xl mx-auto px-5 py-16 space-y-10">
          {HIGHLIGHTS.map((h) => (
            <div key={h.tag} className="grid md:grid-cols-2 gap-8 items-start bg-white border rounded-lg p-6">
              <div>
                <span className="text-xs font-semibold tracking-wide text-brand uppercase">{h.tag}</span>
                <h3 className="text-xl font-bold text-brand-dark mt-2">{h.title}</h3>
                <p className="text-slate-600 mt-3 leading-relaxed">{h.body}</p>
              </div>
              <ul className="space-y-2">
                {h.points.map((p) => (
                  <li key={p} className="flex gap-2 text-sm text-slate-700">
                    <span className="text-brand font-bold shrink-0">✓</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- roles summary ---------- */}
      <section className="max-w-6xl mx-auto px-5 py-16">
        <h2 className="text-2xl font-bold text-brand-dark">Three roles, enforced on the server</h2>
        <p className="text-slate-500 mt-1">
          Hiding a button is not security, so every request is checked again on the backend — including the ones the
          AI assistant makes.
        </p>
        <div className="grid md:grid-cols-3 gap-5 mt-8">
          <div className="bg-white border rounded-lg p-5">
            <h3 className="font-semibold text-brand-dark">Admin</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Company setup, office rules and location, departments and leave types, user access, payroll finalization, the audit log, and company-wide analytics.
            </p>
          </div>
          <div className="bg-white border rounded-lg p-5">
            <h3 className="font-semibold text-brand-dark">HR</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Register employees, salary structures, the daily attendance board, leave approvals, attendance corrections and the monthly payroll draft.
            </p>
          </div>
          <div className="bg-white border rounded-lg p-5">
            <h3 className="font-semibold text-brand-dark">Employee</h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              Check in and out, own attendance calendar, leave with live balance, payslip downloads, and an assistant limited to their own data.
            </p>
          </div>
        </div>
      </section>

      {/* ---------- final CTA ---------- */}
      <section className="bg-brand-dark text-white">
        <div className="max-w-6xl mx-auto px-5 py-14 flex flex-wrap items-center justify-between gap-6">
          <div>
            <h2 className="text-2xl font-bold">Ready to see it with your own data?</h2>
            <p className="text-white/70 mt-1">First-run setup is the only thing between an empty install and a working company.</p>
          </div>
          <div className="flex gap-3">
            <Link to="/login" className="px-6 py-3 rounded bg-brand text-white font-medium hover:opacity-90">
              Sign in
            </Link>
            {firstRun && (
              <Link to="/first-run" className="px-6 py-3 rounded bg-white text-brand-dark font-medium hover:bg-slate-100">
                Set up your company
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* ---------- footer / bottom nav ---------- */}
      <footer className="bg-white">
        <div className="max-w-6xl mx-auto px-5 py-12 grid sm:grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <div className="font-bold text-brand-dark">HCM Lite</div>
            <p className="text-sm text-slate-500 mt-2">AI-assisted human capital management for Admin, HR and Employees.</p>
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Product</div>
            <ul className="space-y-2 text-sm">
              {NAV_LINKS.map((l) => (
                <li key={l.href}>
                  <a href={l.href} className="text-slate-600 hover:text-brand-dark">
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Roles</div>
            <ul className="space-y-2 text-sm">
              <li><a href="#admin" className="text-slate-600 hover:text-brand-dark">Admin</a></li>
              <li><a href="#hr" className="text-slate-600 hover:text-brand-dark">HR</a></li>
              <li><a href="#employee" className="text-slate-600 hover:text-brand-dark">Employee</a></li>
            </ul>
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Account</div>
            <ul className="space-y-2 text-sm">
              <li><Link to="/login" className="text-slate-600 hover:text-brand-dark">Sign in</Link></li>
              {firstRun && <li><Link to="/first-run" className="text-slate-600 hover:text-brand-dark">Set up your company</Link></li>}
            </ul>
          </div>
        </div>
        <div className="border-t">
          <div className="max-w-6xl mx-auto px-5 py-5 text-xs text-slate-400 flex flex-wrap justify-between gap-2">
            <span>© {new Date().getFullYear()} HCM Lite — Saylani Hackathon</span>
            <span>Screenshots shown are the live application with sample data.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
