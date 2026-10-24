# HCM Lite

AI-assisted Human Capital Management for Admin, HR and Employees — built for the Saylani Hackathon (24 Oct 2026).

## Stack

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + React Router
- **Backend:** FastAPI (Python) + SQLAlchemy 2.0
- **Database:** PostgreSQL (any PostgreSQL instance; tables are created automatically on startup, no migration step needed)
- **AI:** Pluggable — Anthropic Claude or OpenAI, chosen via `AI_PROVIDER` in `backend/.env`. Tool calling only; the LLM never touches the database directly.

There is **no seed/dummy data**. The app starts empty: Admin runs first-run setup, HR registers employees, and every dashboard/AI number comes from what people actually do in the app.

## Prerequisites

- Python 3.11+ (3.14 also works)
- Node.js 18+
- A running PostgreSQL server (local, Docker, or any free hosted Postgres)

## 1. Backend setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

- `DATABASE_URL` — point at your Postgres instance, e.g.
  `postgresql+psycopg://hcm_user:hcm_pass@localhost:5432/hcm_lite`
- `JWT_SECRET` — any long random string
- `AI_PROVIDER` — `anthropic` (default) or `openai`
- `AI_API_KEY` — your LLM provider's API key (used server-side only, never sent to the browser)
- `AI_MODEL` — e.g. `claude-sonnet-4-5` (Anthropic) or `gpt-4o-mini` (OpenAI)

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on first startup (`Base.metadata.create_all`). Visit `http://localhost:8000/health` to confirm it's up, or `http://localhost:8000/docs` for the interactive API docs.

## 2. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`.

## 3. Creating the first Admin account

On first load, the frontend checks `/auth/first-run-status`. If the company hasn't been set up yet, it redirects to a **first-run setup** screen where you enter:

- Company name
- Admin email
- Admin password

This creates the company settings row and the first Admin user, and logs you in immediately. From there:

1. **Admin** → Company setup: **set your timezone first** (e.g. `Asia/Karachi`) — attendance dates and the "late after 09:15" rule are evaluated in it, so leaving it at `UTC` on a UTC-hosted server will mark the wrong people late. Then set office hours/grace/half-day rule, weekend days, office location (for optional camera attendance), add departments, designations, leave types (defaults: annual 14, sick 8, casual 10, unpaid unlimited, auto-seeded), public holidays, and create an **HR login**.
2. **HR** signs in (temporary password shown when Admin creates the login; HR is forced to change it on first sign-in), registers employees (creates each employee's login with a temporary password, shown once in the UI).
3. **Employee** signs in, changes password, checks in/out, applies for leave.
4. **HR** approves leave, runs the monthly payroll draft.
5. **Admin** finalizes payroll (locks the month). Employee can then download their payslip PDF.

## 4. Deploying (the hosted link for submission)

The submission needs a **live URL a judge can open**, and it must land on first-run setup so they can create the company themselves. Three pieces: a Postgres database, the backend API, and the frontend static site.

### 4.1 Database

Create a free PostgreSQL instance (Neon, Supabase, or your host's own Postgres) and copy its connection string. Change the scheme to `postgresql+psycopg://` — this project uses psycopg 3:

```
postgresql+psycopg://user:password@host/dbname
```

Tables are created automatically the first time the API starts. There is no migration step.

### 4.2 Backend

Deploy the `backend/` directory as a web service.

- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Python:** 3.12 (pinned in `backend/runtime.txt`; do not use 3.14, several wheels aren't published for it yet)

A `backend/Dockerfile` is included if your host prefers containers.

Environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | the `postgresql+psycopg://...` string from 4.1 |
| `JWT_SECRET` | a long random string |
| `AI_PROVIDER` | `anthropic` or `openai` |
| `AI_API_KEY` | your LLM key — **server-side only, never in the frontend** |
| `AI_MODEL` | e.g. `claude-sonnet-4-5` or `gpt-4o-mini` |
| `FRONTEND_ORIGIN` | your deployed frontend URL, no trailing slash (see 4.4) |

### 4.3 Frontend

Deploy `frontend/` as a static site.

- **Build:** `npm install && npm run build`
- **Publish directory:** `frontend/dist`
- **Environment:** `VITE_API_URL` = your deployed backend URL (baked in at build time, so redeploy after changing it)

`frontend/public/_redirects` ships a `/* /index.html 200` rewrite so deep links like `/hr/employees/1` survive a refresh. That file covers Netlify and Render static sites; on Vercel add the equivalent rewrite in `vercel.json`, and on Nginx use `try_files $uri /index.html`. **Without this rule every page except `/` 404s on reload** — easy to miss until a judge refreshes.

### 4.4 After both are up

1. Set `FRONTEND_ORIGIN` on the backend to the frontend's real URL and redeploy — otherwise every browser request fails CORS.
2. Open the frontend. It should show **first-run setup**, not a login form. If it shows login, the database already has a company in it.
3. Set your **timezone** in Company setup immediately (section 3) — hosted servers usually run in UTC.

### 4.5 Gotchas worth knowing before demo day

- **Free tiers sleep.** Render/Fly free instances spin down when idle and take ~30–60s to wake. Open the hosted link a few minutes before demoing so the first judge request isn't a cold start.
- **No migrations.** Tables are created with `create_all`, which does *not* ALTER existing tables. If you change a model after deploying, drop and recreate the database (fine here — the app is designed to start empty).
- **Never commit `.env`.** Only `.env.example` is in git; real secrets belong in the host's environment settings.

## 5. What's implemented

- **M1 Auth & Access** — JWT login, bcrypt passwords, 3 roles, server-side role + data-scope checks on every route.
- **M2 Organization Setup** — company settings, departments, designations, leave types + quotas, public holidays, HR login management (create/deactivate/reactivate/reset password).
- **M3 Employees** — register (creates login), edit, directory with search/filter/paging, CSV import with dry-run validation (row/field/reason) + CSV export. **Employee 360**: click any name in the directory for one page with their profile, last 30 days of attendance, full leave history and payslips (with PDF download).
- **M4 Attendance** — web check-in/out, late/half-day/missing-checkout status rules, one record per employee per day, attendance corrections (request + approve/reject). The **daily board shows every employee** for the chosen day, not just those who checked in: people with no record are derived as on-leave, weekend/holiday or absent, with a per-status count across the top and a date picker for past days.
- **M5 Leave** — apply/cancel, working-days-only calculation (skips weekends & holidays), overlap and over-balance rejection (422), approval inbox with comments, balance view.
- **M6 Payroll Lite** — salary structure, monthly draft generation (per the brief's gross/tax-slab/proration formulas), Admin-only finalize (locks the run), payslip PDF download.
- **M7 Dashboards & Analytics** — all numbers computed server-side from real records, with working date-range and department filters on the Admin and HR dashboards.
  - **Admin:** headcount, attrition, payroll cost, average salary, attendance rate; charts for headcount by department, payroll cost by department, attendance trend, gender and tenure; plus a recent-activity feed from the audit log.
  - **HR:** headcount, present/on-leave/late today, attendance rate, pending approvals; charts for the attendance trend, attendance rate by department, absenteeism by department and leave days by type; top five late-comers and leave utilization against quota.
  - **Employee:** check-in/out widget, hours this week vs 40, late count, last payslip (with PDF download), leave balance and announcements.
  - **Attendance rate** follows the brief's formula — `(present + late + missing_checkout + 0.5 × half_day) ÷ (working-day records − on_leave)`. Because absent days have no attendance row in this system, the denominator is built from the working days each employee was actually employed for, minus days covered by approved leave.
- **M8 AI Assistant** — chat with tool calling (7 tools scoped to the caller's role/employee_id; no tool ever returns another employee's salary), dashboard "Summarize" button, Smart Leave (free text → pre-filled leave form), policy Q&A grounded in a system-prompt copy of the business rules. Guardrails: AI key server-side only, 15s timeout, ~20 requests/user/hour, every call logged to `ai_logs`, answers labeled "AI-generated" in the UI.
- **M9 Comms & Audit** — announcements (Admin/HR post, everyone reads), in-app notifications shown in a bell with an unread badge in the top right of every page (leave decisions, correction decisions, payslip ready), audit log (actor, action, entity, before/after JSON) visible to Admin.

## 6. What's not done / known gaps

- **Mobile app + camera attendance (bonus, Section 5 of the brief)** — not built. The backend's check-in endpoint already accepts a `source` field (`web`/`camera`) and the `CompanySettings` model already stores office lat/lng/radius, so a camera-based check-in (face-api.js in the browser, or a React Native app) can be added without backend changes beyond adding server-side geofence validation (Haversine) before accepting a `camera` check-in.
- **Other bonus items** (attrition risk score, absence anomaly flags, late-penalty rule, Roman Urdu AI support, dark mode/PWA) are not implemented. The AI system prompt will already attempt to follow Roman Urdu input reasonably well since it's a general LLM, but this hasn't been tuned or tested specifically.
- **Camera check-in is not wired at all.** Note that `POST /attendance/check-in` *accepts* `lat`, `lng`, `accuracy` and `face_detected` but currently **ignores them** — there is no geofence validation, so `source: "camera"` is not yet trustworthy. Treat those fields as placeholders, not a working feature.
- Payroll's day-by-day attendance/leave scan is O(days) per employee per run — fine at hackathon scale, would want a batched query for a larger company.
- The frontend ships as a single ~700 KB bundle (~197 KB gzipped) because the charting library isn't code-split.

### Tests

`backend/tests/smoke_test.py` runs the whole demo script end to end against a throwaway SQLite file — no database server and no AI key needed:

```bash
python backend/tests/smoke_test.py
```

It covers the core flows plus the things most likely to regress: role boundaries (including that the AI tools refuse an Employee company-wide data), the attendance-rate maths against a hand-calculated window, dashboard filters, and two bugs already fixed once — attendance and dashboards disagreeing about "today", and loading the attendance board rewriting past records.

## 7. Live test questions (from the brief, Section 4)

Try these in the AI chat panel once there's real data:

- HR: "How many active employees are in {department}?", "Who came late most often this month?", "What is this month's attendance rate?"
- Employee: "How many sick leaves do I have left this year?"
- Employee: "What is {colleague}'s salary?" → the assistant has no tool that can return another employee's salary, so it politely refuses.
- Employee: "I need next Monday and Tuesday off for my sister's wedding" → use the Smart Leave box on the Leave page.

## 8. Project structure

```
backend/
  app/
    core/        # config, db session, security (JWT, bcrypt)
    models/      # SQLAlchemy models
    schemas/     # Pydantic request/response schemas
    services/    # business logic (one file per module, mirrors Section 3 rules)
    ai/          # tool definitions, system prompts, LLM client (Anthropic/OpenAI)
    api/routes/  # FastAPI routers, one per module
    main.py
  tests/
    smoke_test.py  # end-to-end run of the demo script + RBAC and analytics checks
  Dockerfile
frontend/
  src/
    api/         # axios client
    context/     # auth context
    components/  # Layout, ProtectedRoute, AI chat panel, KPI cards
    pages/
      admin/ hr/ employee/ shared/
```

## 9. Security notes

- Every API route checks role via FastAPI dependencies (`require_admin`, `require_hr`, `require_admin_or_hr`, `require_any`); employee-scoped routes additionally filter by `employee_id` from the JWT, not from client-supplied input.
- Passwords are hashed with bcrypt; employee/HR logins are created with a random temporary password that must be changed on first sign-in.
- The AI provider API key lives only in the backend `.env` — the frontend never sees it and never calls the LLM provider directly.
- Commit `.env.example` only; keep real secrets (`AI_API_KEY`, `DATABASE_URL`, `JWT_SECRET`) in your hosting provider's environment settings, never in git.
