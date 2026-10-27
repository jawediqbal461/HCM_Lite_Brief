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

The submission needs a **live URL a judge can open**, and it must land on first-run setup so they can create the company themselves.

### 4.1 On your own server (one command)

`docker-compose.yml` brings up the whole stack: PostgreSQL, the API, and the frontend served by Caddy with **automatic HTTPS**. The API is proxied at `/api` on the same origin, so there is no CORS to configure and only one certificate to manage.

**You need:** a VPS with SSH, Docker, ports 80 and 443 open, and (for HTTPS) a DNS A record pointing your domain at the server.

```bash
# 1. Install Docker (Ubuntu/Debian; skip if already installed)
curl -fsSL https://get.docker.com | sh

# 2. Get the code
git clone https://github.com/jawediqbal461/HCM_Lite_Brief.git
cd HCM_Lite_Brief

# 3. Set your values — at minimum SITE_ADDRESS, PUBLIC_URL,
#    POSTGRES_PASSWORD, JWT_SECRET and (optionally) AI_API_KEY
cp .env.example .env
nano .env

# 4. Build and start
docker compose up -d --build

# 5. Watch it come up; the API logs "Application startup complete"
docker compose logs -f
```

Then open your domain. That's the link you submit.

**Tip:** test with `SITE_ADDRESS=:80` and the server's IP first. Once that works, switch to your domain and run `docker compose up -d --build` again — Caddy fetches the certificate on its own. Going straight to a domain whose DNS has not propagated yet makes Caddy fail its certificate challenge and the site will not load.

### 4.2 If the server already hosts other sites

Check first — this matters:

```bash
ss -tlnp | grep -E ':80 |:443 '
```

If nginx or Apache is already listening, **do not let this stack take ports 80 and 443**; those sites would go offline. Instead run it on a local port and proxy to it.

In `.env`:

```
SITE_ADDRESS=:80
HTTP_BIND=127.0.0.1:8080
HTTPS_BIND=127.0.0.1:8443
PUBLIC_URL=https://hcm.example.com
```

Then `docker compose up -d --build` and add a vhost to the existing nginx — e.g. `/etc/nginx/conf.d/hcm.conf`:

```nginx
server {
    listen 80;
    server_name hcm.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CSV employee imports
        client_max_body_size 10m;
    }
}
```

```bash
nginx -t && systemctl reload nginx          # -t first: a bad config would drop every site
certbot --nginx -d hcm.example.com          # adds the HTTPS block and auto-renews
```

Here the existing nginx terminates TLS and Caddy just serves the app over plain HTTP on the loopback interface, so nothing is exposed publicly except through nginx.

### 4.3 Day-to-day commands

| Task | Command |
|---|---|
| View logs | `docker compose logs -f api` |
| Restart one service | `docker compose restart api` |
| Deploy new code | `git pull && docker compose up -d --build` |
| Back up the database | `docker compose exec db pg_dump -U hcm hcm_lite > backup.sql` |
| Stop everything | `docker compose down` |
| Start from an empty database | `docker compose down -v` then `docker compose up -d --build` |

`docker compose down -v` deletes **all** volumes, which includes the Let's Encrypt certificates as well as the data. That is fine occasionally, but repeating it many times in a day can hit Let's Encrypt rate limits.

### 4.4 First run on the server

1. Open the site. It should show **first-run setup**, not a login form. If it shows login, the database already has a company in it.
2. Create the company and the Admin account.
3. In Company setup, **set your timezone** (e.g. `Asia/Karachi`) before anyone checks in — the server runs in UTC, and attendance dates and the "late after 09:15" rule are evaluated in the company timezone.

### 4.5 Alternative: a managed platform

If you would rather not run a server, deploy the backend as a web service (build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, Python 3.12 per `backend/runtime.txt`) and the frontend as a static site (build `npm install && npm run build`, publish `frontend/dist`).

In that split setup the two are on different domains, so you must also set `VITE_API_URL` to the backend URL at build time and `FRONTEND_ORIGIN` on the backend to the frontend URL — otherwise every request fails CORS. Use a managed Postgres (Neon, Supabase) and give the backend its connection string as `DATABASE_URL`, with the scheme changed to `postgresql+psycopg://`.

`frontend/public/_redirects` already carries the `/* /index.html 200` rewrite for Netlify and Render static sites. On Vercel add the equivalent in `vercel.json`, on Nginx use `try_files $uri /index.html`. **Without that rule every page except `/` 404s on reload.**

### 4.6 Gotchas worth knowing before demo day

- **Free tiers sleep.** Managed free instances spin down when idle and take 30–60s to wake. Open the link a few minutes before demoing. (A VPS does not have this problem.)
- **Adding a column to a model** is handled: `ensure_additive_columns()` runs at startup and adds any missing plain columns to existing tables, so a deploy does not break a database that predates the change. Anything that needs data moved or a column dropped is **not** covered — that deserves a real migration tool. Tables themselves are still created by `create_all`.
- **Never commit `.env`.** Only the `.env.example` files are in git; real secrets stay on the server.

## 5. What's implemented

- **M1 Auth & Access** — JWT login, bcrypt passwords, 3 roles, server-side role + data-scope checks on every route.
- **M2 Organization Setup** — company settings, departments, designations, leave types + quotas, public holidays, HR login management (create/deactivate/reactivate/reset password).
- **M3 Employees** — register (creates login), **edit any detail including the salary structure** (HR manages, Admin views), directory with search, department and status filters plus server-side paging, CSV import with dry-run validation (row/field/reason) + CSV export.
- **Data tables, filters and exports** — the lists people actually work in are filtered and paged on the server, not trimmed in the browser:

  | Table | Filters | Paged | CSV |
  |---|---|---|---|
  | Employees | search, department, status | ✅ | ✅ |
  | Leave records | search, status, type, department, date range | ✅ | ✅ |
  | Attendance board | day, search, department, status | — (one day) | ✅ |
  | Audit log | action, entity, date range | ✅ | ✅ |
  | Payroll run | department | — | ✅ |
  | My attendance / leave / payslips | month, year, status, type | — | — |

  Every export honours the filters currently applied, so what downloads is what you are looking at, and each one stays inside the caller's role.
- **Reports** — period summaries with totals, each exportable to CSV, listed per role so nobody is offered a report they cannot run:

  | Role | Reports |
  |---|---|
  | Admin & HR | Attendance register, Leave register, Late arrivals, Payroll register, Headcount & attrition |
  | Employee | My attendance, My leave statement, My payslip history |

  All eight share one response shape (columns, rows, totals), so a single screen renders any of them and one endpoint exports any of them — adding a report means writing one function. Parameters follow the report: a register asks for a date range, payroll asks for a month, a statement asks for a year. The late-arrivals report uses the same rule as payroll, so the penalty days it shows are the ones actually deducted. **Employee 360**: click any name in the directory for one page with their profile, last 30 days of attendance, full leave history and payslips (with PDF download).
- **M4 Attendance** — web check-in/out, late/half-day/missing-checkout status rules, one record per employee per day, attendance corrections (request + approve/reject). The **daily board shows every employee** for the chosen day, not just those who checked in: people with no record are derived as on-leave, weekend/holiday or absent, with a per-status count across the top and a date picker for past days.
- **Camera attendance (the brief's +10 bonus)** — browser check-in that is accepted only when exactly one face is in frame *and* the device is inside the office geofence. Face detection runs on-device with face-api.js (tiny detector, weights served from `/models`, loaded lazily so they never touch the main bundle); **no photo is stored, only the result**. Every rule is re-checked on the server — one face, GPS accuracy within 100 m, and Haversine distance within the configured radius — so the decision cannot be faked by editing the client. Admin sets the office point with one click from Company setup.
- **Public landing page** at `/` with a sticky header nav, a hero, nine-module overview, a "from empty install to working company" walkthrough, three role sections (Admin/HR/Employee) each built around a real screenshot of that role's screens, a strip of everyday-operations screenshots, a reports-and-insights section, the camera-attendance and AI-assistant deep dives, and a footer nav. Every screenshot is the actual running app with realistic seeded data (`backend/scripts/seed_demo.py`, a dev-only tool — never run against a real deployment), not stock art. A "Set up your company" call to action appears only while the install is still unconfigured. There is deliberately **no public self-registration**: employee logins are created by HR, as the brief's access model requires.
- **M5 Leave** — apply/cancel, working-days-only calculation (skips weekends & holidays), overlap and over-balance rejection (422), approval inbox with comments, balance view.
- **M6 Payroll Lite** — salary structure, monthly draft generation (per the brief's gross/tax-slab/proration formulas), Admin-only finalize (locks the run), payslip PDF download. Includes the bonus **late-penalty rule**: every 3 late arrivals in a month cost half a day's pay, shown as its own line on the payslip rather than folded silently into the total. Partial groups do not count, so two lates cost nothing.
- **Insights (bonus)** — an Admin/HR page with **attrition risk** and **absence anomaly flags**, computed from the last 90 days. Both are explainable heuristics, never predictions: each risk score ships with the factors that produced it (absence rate, lateness, leave use, tenure, a recent rise in absence), and each anomaly says exactly what it saw — absences clustering next to weekends, repeated isolated single days, a rising trend, or frequent lateness. Nothing here decides anything on its own; it is a list of things worth a conversation.
- **M7 Dashboards & Analytics** — all numbers computed server-side from real records, with working date-range and department filters on the Admin and HR dashboards.
  - **Admin:** headcount, attrition, payroll cost, average salary, attendance rate; charts for headcount by department, payroll cost by department, attendance trend, gender and tenure; plus a recent-activity feed from the audit log.
  - **HR:** headcount, present/on-leave/late today, attendance rate, pending approvals; charts for the attendance trend, attendance rate by department, absenteeism by department and leave days by type; top five late-comers and leave utilization against quota.
  - **Employee:** check-in/out widget, hours this week vs 40, late count, last payslip (with PDF download), leave balance and announcements.
  - **Attendance rate** follows the brief's formula — `(present + late + missing_checkout + 0.5 × half_day) ÷ (working-day records − on_leave)`. Because absent days have no attendance row in this system, the denominator is built from the working days each employee was actually employed for, minus days covered by approved leave.
- **M8 AI Assistant** — chat with tool calling (7 tools scoped to the caller's role/employee_id; no tool ever returns another employee's salary), dashboard "Summarize" button, Smart Leave (free text → pre-filled leave form), policy Q&A grounded in a system-prompt copy of the business rules. Guardrails: AI key server-side only, 15s timeout, ~20 requests/user/hour, every call logged to `ai_logs`, answers labeled "AI-generated" in the UI.
- **M9 Comms & Audit** — announcements (Admin/HR post, everyone reads), in-app notifications shown in a bell with an unread badge in the top right of every page (leave decisions, correction decisions, payslip ready), audit log (actor, action, entity, before/after JSON) visible to Admin.

## 6. What's not done / known gaps

- **A native mobile app** is not built. Camera check-in runs in the browser instead, which the brief allows ("the same camera check can also run in the web app on a laptop or phone browser").
- **Dark mode and PWA** are not implemented.
- **Roman Urdu AI support** has not been tuned or tested. The assistant will likely cope reasonably since it is a general LLM, but nothing was done deliberately and no claim is made about it.
- **Camera check-in needs HTTPS.** Browsers only expose the camera and geolocation in a secure context, so over plain `http://` the feature hides itself and explains why. The face-detection path has been exercised end to end except on a machine with no webcam, where it fails with a clear message rather than silently.
- **Face matching against an enrolled face is not implemented** — the check confirms that exactly one face is present, not *whose* face it is. That is the brief's "extra bonus" tier; the current level is the one it asks for.
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
  Dockerfile       # API image
docker-compose.yml # whole stack: Postgres + API + frontend/Caddy
.env.example       # deployment settings (copy to .env on the server)
frontend/
  src/
    api/         # axios client
    context/     # auth context
    components/  # Layout, ProtectedRoute, AI chat panel, KPI cards
    pages/
      admin/ hr/ employee/ shared/
  Caddyfile        # static serving + /api reverse proxy + automatic HTTPS
  Dockerfile       # builds the app, then serves it with Caddy
```

## 9. Security notes

- Every API route checks role via FastAPI dependencies (`require_admin`, `require_hr`, `require_admin_or_hr`, `require_any`); employee-scoped routes additionally filter by `employee_id` from the JWT, not from client-supplied input.
- Passwords are hashed with bcrypt; employee/HR logins are created with a random temporary password that must be changed on first sign-in.
- The AI provider API key lives only in the backend `.env` — the frontend never sees it and never calls the LLM provider directly.
- Commit `.env.example` only; keep real secrets (`AI_API_KEY`, `DATABASE_URL`, `JWT_SECRET`) in your hosting provider's environment settings, never in git.
