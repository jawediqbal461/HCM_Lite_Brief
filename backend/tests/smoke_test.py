"""End-to-end smoke test for HCM Lite.

Walks the whole demo script against a throwaway SQLite database — first-run setup,
HR and employee logins, check-in/out, leave apply/approve, payroll run and finalize,
payslip PDF — then asserts the role boundaries (an Employee must not reach other
people's data, including through the AI tools), the analytics maths, and a few
regressions we have already been bitten by.

Run it from anywhere:    python backend/tests/smoke_test.py
No database server and no AI key required; it runs fully offline.
"""

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(__file__).resolve().parent / "smoke_test.db"

# Must be set before app.core.config is imported.
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["AI_API_KEY"] = ""  # empty: the AI layer must degrade gracefully, not call out

sys.path.insert(0, str(BACKEND_ROOT))

if DB_PATH.exists():
    DB_PATH.unlink()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
client.__enter__()


def check(label, resp, expect=200):
    ok = resp.status_code == expect
    print(f"{'OK' if ok else 'FAIL'} {label}: {resp.status_code}", "" if ok else resp.text[:300])
    assert ok, f"{label} failed: {resp.status_code} {resp.text}"
    return resp.json() if resp.content else None


# 1. first-run status
d = check("first-run-status", client.get("/auth/first-run-status"))
assert d["first_run"] is True

# 2. first-run setup
d = check(
    "first-run-setup",
    client.post(
        "/auth/first-run-setup",
        json={"company_name": "Acme Corp", "admin_email": "admin@acme.com", "admin_password": "AdminPass123"},
    ),
)
admin_token = d["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}

# 3. company settings
d = check("get settings", client.get("/org/settings", headers=admin_headers))
check(
    "update settings",
    client.put(
        "/org/settings",
        headers=admin_headers,
        json={"office_lat": 24.86, "office_lng": 67.0, "office_radius_m": 200},
    ),
)

# 4. department
d = check("create dept", client.post("/org/departments", headers=admin_headers, json={"name": "Engineering"}))
dept_id = d["id"]

# 5. create HR login
d = check(
    "create hr",
    client.post(
        "/org/hr-users",
        headers=admin_headers,
        json={"full_name": "HR Person", "email": "hr@acme.com", "password": "HrPass123"},
    ),
)

# 6. HR login
d = check("hr login", client.post("/auth/login", json={"email": "hr@acme.com", "password": "HrPass123"}))
hr_token = d["access_token"]
hr_headers = {"Authorization": f"Bearer {hr_token}"}
assert d["must_change_password"] is True

check(
    "hr change password",
    client.post("/auth/change-password", headers=hr_headers, json={"old_password": "HrPass123", "new_password": "HrPass456!"}),
)

# re-login with new password
d = check("hr login 2", client.post("/auth/login", json={"email": "hr@acme.com", "password": "HrPass456!"}))
hr_token = d["access_token"]
hr_headers = {"Authorization": f"Bearer {hr_token}"}

# 7. register employee
d = check(
    "register employee",
    client.post(
        "/employees",
        headers=hr_headers,
        json={
            "code": "EMP001",
            "full_name": "Jane Doe",
            "email": "jane@acme.com",
            "department_id": dept_id,
            "date_of_joining": "2026-01-01",
            "basic_salary": 100000,
        },
    ),
)
emp_temp_password = d["temporary_password"]
employee_id = d["employee"]["id"]
print("employee temp password:", emp_temp_password)

# 8. employee login + change password
d = check("employee login", client.post("/auth/login", json={"email": "jane@acme.com", "password": emp_temp_password}))
emp_token = d["access_token"]
emp_headers = {"Authorization": f"Bearer {emp_token}"}
check(
    "employee change password",
    client.post("/auth/change-password", headers=emp_headers, json={"old_password": emp_temp_password, "new_password": "JanePass123!"}),
)
d = check("employee login 2", client.post("/auth/login", json={"email": "jane@acme.com", "password": "JanePass123!"}))
emp_token = d["access_token"]
emp_headers = {"Authorization": f"Bearer {emp_token}"}

# 9. check-in / check-out
d = check("check-in", client.post("/attendance/check-in", headers=emp_headers, json={"source": "web"}))
print("check-in status:", d["status"])
d2 = check("check-in dup (409)", client.post("/attendance/check-in", headers=emp_headers, json={"source": "web"}), expect=409)
d = check("check-out", client.post("/attendance/check-out", headers=emp_headers, json={}))
print("check-out status:", d["status"])

# Regression: the attendance module and the dashboards must agree on what "today" is.
# They previously disagreed (UTC date vs server-local date), so the dashboard showed
# "not checked in" while a second check-in was rejected with 409.
me = check("employee dashboard agrees on today", client.get("/dashboards/me", headers=emp_headers))
assert me["checked_in"] is True, f"dashboard disagrees with attendance about today: {me}"
assert me["checked_out"] is True, me
print("OK attendance and dashboard agree on today (checked in + out)")

# Timezone is configurable and round-trips.
tz_settings = check(
    "set company timezone",
    client.put("/org/settings", headers=admin_headers, json={"timezone": "Asia/Karachi"}),
)
assert tz_settings["timezone"] == "Asia/Karachi", tz_settings
check("reset company timezone", client.put("/org/settings", headers=admin_headers, json={"timezone": "UTC"}))
print("OK company timezone setting round-trips")

# 10. leave types + apply
d = check("leave types (employee)", client.get("/org/leave-types", headers=emp_headers))
casual = next(lt for lt in d if lt["name"] == "casual")
d = check(
    "apply leave",
    client.post(
        "/leave/apply",
        headers=emp_headers,
        json={"leave_type_id": casual["id"], "start_date": "2026-11-02", "end_date": "2026-11-03", "reason": "Wedding"},
    ),
)
leave_id = d["id"]
print("leave days:", d["days"])

# 11. HR approves leave
d = check("leave inbox", client.get("/leave/inbox", headers=hr_headers))
assert len(d) == 1
d = check("decide leave", client.post(f"/leave/{leave_id}/decide", headers=hr_headers, json={"approve": True, "comment": "ok"}))
assert d["status"] == "approved"

# 12. leave balance
d = check("leave balance", client.get("/leave/balance", headers=emp_headers))
print("balance:", d)

# 13. payroll draft + finalize
d = check("create payroll draft", client.post("/payroll/runs", headers=hr_headers, json={"month": 1, "year": 2026}))
run_id = d["id"]
print("payslips in draft:", len(d["payslips"]), d["payslips"])
d = check("finalize payroll", client.post(f"/payroll/runs/{run_id}/finalize", headers=admin_headers))
assert d["status"] == "finalized"

# 14. employee payslips + pdf
d = check("my payslips", client.get("/payroll/payslips/mine", headers=emp_headers))
assert len(d) == 1
slip_id = d[0]["id"]
r = client.get(f"/payroll/payslips/{slip_id}/pdf", headers=emp_headers)
assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
print("OK payslip pdf bytes:", len(r.content))

# 15. dashboards
check("admin dashboard", client.get("/dashboards/admin", headers=admin_headers))
check("hr dashboard", client.get("/dashboards/hr", headers=hr_headers))
check("employee dashboard", client.get("/dashboards/me", headers=emp_headers))

# 16. AI chat without key -> should degrade gracefully, not crash (AI_API_KEY is fake, provider call will fail -> AIError caught)
r = client.post("/ai/chat", headers=emp_headers, json={"message": "How many sick leaves do I have left?"})
print("ai chat status:", r.status_code, r.json() if r.status_code == 200 else r.text[:200])
assert r.status_code == 200  # should degrade gracefully with error message, not 500

# 17. smart leave with bad key -> graceful fallback
r = client.post("/leave/smart", headers=emp_headers, json={"text": "need next monday off"})
print("smart leave status:", r.status_code, r.json() if r.status_code == 200 else r.text[:200])
assert r.status_code == 200

# 18. RBAC check: employee cannot see org settings management endpoints meant for admin/hr-only write, cannot access audit log
r = client.get("/audit-log", headers=emp_headers)
assert r.status_code == 403, r.text
print("OK RBAC: employee blocked from audit log (403)")

r = client.get("/employees", headers=emp_headers)
assert r.status_code == 403, r.text
print("OK RBAC: employee blocked from employee directory (403)")

# 19. employee cannot view another employee's profile
r = client.get(f"/employees/{employee_id + 999}", headers=emp_headers)
assert r.status_code in (403, 404), r.text
print("OK RBAC: employee blocked from others' profile")

# 20. AI tool role scoping (tested directly — no live LLM key needed)
from app.ai.tools import run_tool
from app.api.deps import CurrentUser
from app.core.database import SessionLocal

db = SessionLocal()
emp_user = CurrentUser(id=3, email="jane@acme.com", role="employee", employee_id=employee_id)
hr_user = CurrentUser(id=2, email="hr@acme.com", role="hr", employee_id=None)

for tool_name in ("get_headcount", "get_late_comers", "get_leave_summary"):
    res = run_tool(db, emp_user, tool_name, {})
    assert "error" in res, f"{tool_name} leaked company data to an Employee: {res}"
    print(f"OK AI scoping: {tool_name} refused for Employee")

res = run_tool(db, emp_user, "get_attendance_summary", {})
assert res.get("scope") == "own", f"attendance summary not own-scoped for Employee: {res}"
print("OK AI scoping: get_attendance_summary is own-scoped for Employee")

res = run_tool(db, hr_user, "get_headcount", {})
assert "headcount" in res, f"HR wrongly blocked from headcount: {res}"
res = run_tool(db, hr_user, "get_late_comers", {})
assert "top_late_comers" in res, f"HR wrongly blocked from late-comers: {res}"
print("OK AI scoping: HR still gets company-wide data")
db.close()

# 21. Admin can view attendance corrections and all leave records
check("admin views corrections", client.get("/attendance/corrections/pending", headers=admin_headers))
d = check("admin views all leave", client.get("/leave", headers=admin_headers))
assert d["total"] == 1, f"expected the approved leave record, got {d}"
r = client.get("/leave", headers=emp_headers)
assert r.status_code == 403, r.text
print("OK RBAC: employee blocked from all-leave records (403)")

# 22. Admin and HR can download any payslip PDF
for label, headers in (("admin", admin_headers), ("hr", hr_headers)):
    r = client.get(f"/payroll/payslips/{slip_id}/pdf", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf", r.text
    print(f"OK {label} downloaded payslip PDF ({len(r.content)} bytes)")

# 23. CSV export requires auth
r = client.get("/employees/export-csv", headers=hr_headers)
assert r.status_code == 200 and "code,full_name" in r.text, r.text
r = client.get("/employees/export-csv")
assert r.status_code in (401, 403), r.text
print("OK CSV export works for HR and rejects unauthenticated callers")

# 24. Analytics: attendance rate, trend, breakdowns and working filters
hr = check("hr dashboard (analytics)", client.get("/dashboards/hr", headers=hr_headers))
for key in ("attendance_rate", "trend", "attendance_by_department", "leave_by_type"):
    assert key in hr, f"HR dashboard missing {key}"
assert len(hr["trend"]) > 0, "attendance trend is empty"
assert all({"date", "present", "late", "absent"} <= set(point) for point in hr["trend"]), hr["trend"][:2]
print(f"OK trend has {len(hr['trend'])} working days")

# Exercise the attendance-rate formula against a hand-calculated window.
# Mon 5 Oct 2026 - Fri 9 Oct 2026 is 5 working days for our 1 employee.
# One full day present (1.0) + one half day (0.5) out of 5 expected days = 30%.
from datetime import date as _date
from app.models.attendance import Attendance as _Attendance

db = SessionLocal()
db.add(_Attendance(employee_id=employee_id, date=_date(2026, 10, 5), status="present", source="web"))
db.add(_Attendance(employee_id=employee_id, date=_date(2026, 10, 6), status="half_day", source="web"))
db.commit()
db.close()

window = check(
    "attendance rate window",
    client.get("/dashboards/hr", headers=hr_headers, params={"start": "2026-10-05", "end": "2026-10-09"}),
)
assert window["attendance_rate"] == 30.0, f"expected 30.0%, got {window['attendance_rate']}"
assert window["absent_count"] == 3, f"expected 3 absent days, got {window['absent_count']}"
dept_row = window["attendance_by_department"][0]
assert dept_row["attendance_rate"] == 30.0 and dept_row["absenteeism_pct"] == 60.0, dept_row
print("OK attendance rate maths: 1 present + 0.5 half day over 5 working days = 30.0%")
print(f"OK absenteeism by department: {dept_row['department']} {dept_row['absenteeism_pct']}%")

adm = check("admin dashboard (analytics)", client.get("/dashboards/admin", headers=admin_headers))
for key in ("headcount_by_department", "gender_breakdown", "tenure_breakdown", "recent_audit", "attendance_rate"):
    assert key in adm, f"Admin dashboard missing {key}"
assert len(adm["recent_audit"]) > 0, "audit feed is empty"
assert sum(b["count"] for b in adm["tenure_breakdown"]) == adm["headcount"], adm["tenure_breakdown"]
print(f"OK admin breakdowns: depts={adm['headcount_by_department']} tenure={adm['tenure_breakdown']}")

# department filter actually narrows the result
in_dept = check("hr dashboard filtered to dept", client.get("/dashboards/hr", headers=hr_headers, params={"department_id": dept_id}))
assert in_dept["headcount"] == 1, in_dept["headcount"]
other = check("hr dashboard filtered to empty dept", client.get("/dashboards/hr", headers=hr_headers, params={"department_id": dept_id + 999}))
assert other["headcount"] == 0 and other["attendance_rate"] == 0.0, other
print("OK department filter narrows dashboard results")

# date-range filter changes the window
narrow = check(
    "hr dashboard narrow range",
    client.get("/dashboards/hr", headers=hr_headers, params={"start": "2026-01-05", "end": "2026-01-09"}),
)
assert narrow["range"] == {"start": "2026-01-05", "end": "2026-01-09"}, narrow["range"]
assert len(narrow["trend"]) == 5, f"expected 5 working days Mon-Fri, got {len(narrow['trend'])}"
print("OK date-range filter applied (5 working days in 05-09 Jan 2026)")

# 25. Names instead of raw IDs across the HR-facing tables
board = check("attendance board", client.get("/attendance/board", headers=hr_headers))
assert len(board) == 1, f"board should list every employee, got {board}"
assert board[0]["employee_name"] == "Jane Doe" and board[0]["employee_code"] == "EMP001", board[0]
assert board[0]["department"] == "Engineering", board[0]
print(f"OK board shows names: {board[0]['employee_name']} ({board[0]['department']})")

leave_rows = check("leave records carry names", client.get("/leave", headers=admin_headers))["items"]
assert leave_rows[0]["employee_name"] == "Jane Doe", leave_rows[0]
assert leave_rows[0]["leave_type_name"] == "casual", leave_rows[0]

run = check("payroll run carries names", client.get(f"/payroll/runs/{run_id}", headers=hr_headers))
assert run["payslips"][0]["employee_name"] == "Jane Doe", run["payslips"][0]
print("OK leave records and payslips carry employee names")

# 26. The board must include employees who never checked in (previously invisible)
# Register a second employee who has no attendance at all.
second = check(
    "register second employee",
    client.post(
        "/employees",
        headers=hr_headers,
        json={
            "code": "EMP002",
            "full_name": "Omar Siddiqui",
            "email": "omar@acme.com",
            "gender": "Male",
            "department_id": dept_id,
            "date_of_joining": "2026-02-01",
            "basic_salary": 80000,
        },
    ),
)
second_id = second["employee"]["id"]

board = check("board includes non-checked-in staff", client.get("/attendance/board", headers=hr_headers))
names = {row["employee_name"]: row["status"] for row in board}
assert "Omar Siddiqui" in names, f"employee with no attendance row is missing from the board: {names}"
print(f"OK board statuses for everyone: {names}")

# On a working day with no record and no leave, the status must read 'absent'.
monday = check(
    "board on a past working day",
    client.get("/attendance/board", headers=hr_headers, params={"day": "2026-10-07"}),
)
omar_row = next(r for r in monday if r["employee_name"] == "Omar Siddiqui")
assert omar_row["status"] == "absent", omar_row
jane_row = next(r for r in monday if r["employee_name"] == "Jane Doe")
assert jane_row["status"] == "absent", jane_row
print("OK absent staff appear on the board for a past working day")

# A weekend day is labelled as such rather than marking everyone absent.
weekend = check(
    "board on a weekend",
    client.get("/attendance/board", headers=hr_headers, params={"day": "2026-10-11"}),
)
assert all(r["status"] in ("weekend", "on_leave") for r in weekend), weekend
print("OK weekend days are not counted as absence on the board")

# 26b. Loading the board must not rewrite history.
# An absent day raised for correction has no check-out time either, and was previously
# swept into "missing_checkout" by the board's finalize pass.
check(
    "request correction on an absent day",
    client.post("/attendance/corrections", headers=emp_headers, json={"date": "2026-10-07", "reason": "Was on site, forgot to check in"}),
)
check("board after correction request", client.get("/attendance/board", headers=hr_headers))
cal = check(
    "attendance after board sweep",
    client.get("/attendance/calendar", headers=hr_headers, params={"employee_id": employee_id, "start": "2026-10-05", "end": "2026-10-09"}),
)
by_date = {row["date"]: row["status"] for row in cal}
assert by_date["2026-10-07"] == "absent", f"correction day was rewritten: {by_date}"
assert by_date["2026-10-05"] == "present", f"synthetic present day was rewritten: {by_date}"
assert by_date["2026-10-06"] == "half_day", f"synthetic half day was rewritten: {by_date}"
print("OK loading the board no longer rewrites absent/corrected days")

# The attendance rate must therefore stay stable after a board load.
after = check(
    "attendance rate after board load",
    client.get("/dashboards/hr", headers=hr_headers, params={"start": "2026-10-05", "end": "2026-10-09"}),
)
assert after["attendance_rate"] == 15.0, f"expected 15.0% for 2 employees over 5 days, got {after['attendance_rate']}"
print("OK attendance rate stable after board load (15.0% across 2 employees)")

# 27. Employee 360 data sources
check("360 profile", client.get(f"/employees/{employee_id}", headers=hr_headers))
check("360 attendance", client.get("/attendance/calendar", headers=hr_headers, params={"employee_id": employee_id, "start": "2026-10-01", "end": "2026-10-31"}))
emp_leave = check("360 leave", client.get("/leave", headers=hr_headers, params={"employee_id": employee_id}))
assert emp_leave["total"] == 1 and emp_leave["items"][0]["employee_id"] == employee_id, emp_leave
other_leave = check("360 leave for other employee", client.get("/leave", headers=hr_headers, params={"employee_id": second_id}))
assert other_leave["total"] == 0, other_leave
emp_slips = check("360 payslips", client.get("/payroll/payslips", headers=hr_headers, params={"employee_id": employee_id}))
assert len(emp_slips) == 1, emp_slips
r = client.get("/payroll/payslips", headers=emp_headers, params={"employee_id": employee_id})
assert r.status_code == 403, r.text
print("OK Employee 360 lookups work and stay staff-only")

# 28. Notifications are readable and can be marked read
notes = check("notifications", client.get("/notifications", headers=emp_headers))
assert len(notes) >= 1, "employee should have a leave-decision notification"
unread_before = sum(1 for n in notes if not n["read"])
assert unread_before >= 1, notes
check("mark notification read", client.post(f"/notifications/{notes[0]['id']}/read", headers=emp_headers))
notes_after = check("notifications after read", client.get("/notifications", headers=emp_headers))
assert sum(1 for n in notes_after if not n["read"]) == unread_before - 1, notes_after
print(f"OK notifications: {len(notes)} total, unread count drops after marking read")

# 29. Camera check-in: every rule is enforced server-side
from app.services.geofence import check_camera_attendance, haversine_metres


class _Settings:
    def __init__(self, lat=24.8607, lng=67.0011, radius=150):
        self.office_lat = lat
        self.office_lng = lng
        self.office_radius_m = radius


OFFICE = _Settings()
AT_DESK = {"lat": 24.8607, "lng": 67.0011, "accuracy": 20.0}

# A known distance: Karachi -> Lahore is roughly 1,020 km.
km = haversine_metres(24.8607, 67.0011, 31.5204, 74.3587) / 1000
assert 1000 < km < 1050, f"haversine looks wrong: {km:.0f} km"
print(f"OK haversine sanity: Karachi-Lahore {km:.0f} km")

ok = check_camera_attendance(OFFICE, face_detected=True, faces_count=1, **AT_DESK)
assert ok.ok, ok.reason
print(f"OK camera check-in accepted at the office ({ok.distance_m:.0f} m away)")

cases = [
    ("no face", dict(face_detected=False, faces_count=0, **AT_DESK), "no face"),
    ("two faces", dict(face_detected=True, faces_count=2, **AT_DESK), "more than one"),
    ("no location", dict(face_detected=True, faces_count=1, lat=None, lng=None, accuracy=None), "location unavailable"),
    ("vague GPS", dict(face_detected=True, faces_count=1, lat=24.8607, lng=67.0011, accuracy=250.0), "not precise"),
    ("far away", dict(face_detected=True, faces_count=1, lat=31.5204, lng=74.3587, accuracy=10.0), "outside"),
]
for label, kwargs, expected in cases:
    res = check_camera_attendance(OFFICE, **kwargs)
    assert not res.ok, f"{label} should have been rejected"
    assert expected in res.reason.lower(), f"{label}: unexpected reason {res.reason!r}"
    print(f"OK camera check-in rejected ({label})")

no_office = check_camera_attendance(_Settings(lat=None, lng=None), face_detected=True, faces_count=1, **AT_DESK)
assert not no_office.ok and "office location" in no_office.reason.lower(), no_office.reason
print("OK camera check-in refused when the office location is not configured")

# And through the API: a camera check-in without a face must not create a record.
r = client.post(
    "/attendance/check-in",
    headers=emp_headers,
    json={"source": "camera", "face_detected": False, "faces_count": 0, "lat": 24.8607, "lng": 67.0011, "accuracy": 10},
)
assert r.status_code == 422, f"expected 422, got {r.status_code} {r.text[:200]}"
print("OK API rejects a camera check-in with no face (422)")

# 30. User & access management, including the guards that stop a lock-out
users = check("list users", client.get("/org/users", headers=admin_headers))
by_email = {u["email"]: u for u in users}
assert {"admin@acme.com", "hr@acme.com", "jane@acme.com"} <= set(by_email), by_email.keys()
assert by_email["jane@acme.com"]["employee_name"] == "Jane Doe", by_email["jane@acme.com"]
assert by_email["hr@acme.com"]["employee_id"] is None, by_email["hr@acme.com"]
print(f"OK admin can list {len(users)} logins with their linked employees")

r = client.get("/org/users", headers=hr_headers)
assert r.status_code == 403, r.text
r = client.get("/org/users", headers=emp_headers)
assert r.status_code == 403, r.text
print("OK user list is Admin-only (HR and Employee both 403)")

admin_user = by_email["admin@acme.com"]
hr_user = by_email["hr@acme.com"]
jane_user = by_email["jane@acme.com"]

# An admin must not be able to strand the company without an admin.
r = client.patch(f"/org/users/{admin_user['id']}/role", headers=admin_headers, json={"role": "hr"})
assert r.status_code == 400 and "own role" in r.json()["detail"].lower(), r.text
print("OK admin cannot change their own role")

r = client.post(f"/org/users/{admin_user['id']}/deactivate", headers=admin_headers)
assert r.status_code == 400 and "own login" in r.json()["detail"].lower(), r.text
print("OK admin cannot deactivate their own login")

# An HR login has no employee record, so it cannot become an Employee.
r = client.patch(f"/org/users/{hr_user['id']}/role", headers=hr_headers, json={"role": "employee"})
assert r.status_code == 403, r.text
r = client.patch(f"/org/users/{hr_user['id']}/role", headers=admin_headers, json={"role": "employee"})
assert r.status_code == 400 and "employee record" in r.json()["detail"].lower(), r.text
print("OK a login with no employee record cannot be made an Employee")

r = client.patch(f"/org/users/{hr_user['id']}/role", headers=admin_headers, json={"role": "owner"})
assert r.status_code == 400, r.text
print("OK unknown roles are rejected")

# A real promotion and demotion round-trip.
d = check("promote employee to hr", client.patch(f"/org/users/{jane_user['id']}/role", headers=admin_headers, json={"role": "hr"}))
assert d["role"] == "hr", d
d = check("demote back to employee", client.patch(f"/org/users/{jane_user['id']}/role", headers=admin_headers, json={"role": "employee"}))
assert d["role"] == "employee", d
print("OK role can be changed both ways for a login with an employee record")

# Deactivate blocks sign-in, reactivate restores it.
check("deactivate hr", client.post(f"/org/users/{hr_user['id']}/deactivate", headers=admin_headers))
r = client.post("/auth/login", json={"email": "hr@acme.com", "password": "HrPass456!"})
assert r.status_code == 401, f"deactivated login still works: {r.text}"
check("reactivate hr", client.post(f"/org/users/{hr_user['id']}/reactivate", headers=admin_headers))
check("hr can sign in again", client.post("/auth/login", json={"email": "hr@acme.com", "password": "HrPass456!"}))
print("OK deactivation blocks sign-in and reactivation restores it")

# Password reset issues a working temporary password that must be changed.
d = check("reset hr password", client.post(f"/org/users/{hr_user['id']}/reset-password", headers=admin_headers))
temp = d["temporary_password"]
r = client.post("/auth/login", json={"email": "hr@acme.com", "password": "HrPass456!"})
assert r.status_code == 401, "the old password still works after a reset"
d = check("sign in with the temporary password", client.post("/auth/login", json={"email": "hr@acme.com", "password": temp}))
assert d["must_change_password"] is True, d
print("OK password reset invalidates the old password and forces a change")

# 31. A shared demo login can skip the forced password change
d = check(
    "create HR login without forced change",
    client.post(
        "/org/hr-users",
        headers=admin_headers,
        json={
            "full_name": "Demo HR",
            "email": "demo-hr@acme.com",
            "password": "demo-hr-password",
            "require_password_change": False,
        },
    ),
)
assert d["must_change_password"] is False, d
login = check("demo login works as set", client.post("/auth/login", json={"email": "demo-hr@acme.com", "password": "demo-hr-password"}))
assert login["must_change_password"] is False, login
print("OK a shared login can be created without forcing a password change")

# ...while the default still forces one.
d = check(
    "create HR login with the default",
    client.post(
        "/org/hr-users",
        headers=admin_headers,
        json={"full_name": "Normal HR", "email": "normal-hr@acme.com", "password": "temp-password-1"},
    ),
)
assert d["must_change_password"] is True, d
print("OK the default still requires a password change on first sign-in")

# 32. Anyone can change their own password from their profile
demo_headers = {"Authorization": f"Bearer {login['access_token']}"}
check("profile: who am i", client.get("/auth/me", headers=demo_headers))
check(
    "change own password",
    client.post("/auth/change-password", headers=demo_headers, json={"old_password": "demo-hr-password", "new_password": "a-much-longer-one"}),
)
r = client.post("/auth/login", json={"email": "demo-hr@acme.com", "password": "demo-hr-password"})
assert r.status_code == 401, "the old password still works"
check("sign in with the new password", client.post("/auth/login", json={"email": "demo-hr@acme.com", "password": "a-much-longer-one"}))
r = client.post("/auth/change-password", headers=demo_headers, json={"old_password": "wrong-one", "new_password": "another-long-one"})
assert r.status_code == 400, r.text
print("OK a user can change their own password, and the old one stops working")

# An HR login has no employee record, so the profile page's details call 404s cleanly.
r = client.get("/employees/me", headers=demo_headers)
assert r.status_code == 400, r.text
print("OK profile handles a login with no employee record")

# 33. Late penalty rule: every 3 lates in a month cost half a day
from app.services.payroll_service import LATES_PER_PENALTY, PENALTY_DAYS

assert (LATES_PER_PENALTY, PENALTY_DAYS) == (3, 0.5), "the brief's rule is 3 lates = 0.5 day"

db = SessionLocal()
# Four late arrivals for Omar on past working days in Oct 2026 -> one penalty, not two.
# They must be in the past: insights only look back, never forward.
for day in (1, 2, 12, 13):
    db.add(_Attendance(employee_id=second_id, date=_date(2026, 10, day), status="late", source="web"))
db.commit()
db.close()

run = check("payroll with lates", client.post("/payroll/runs", headers=hr_headers, json={"month": 10, "year": 2026}))
slips = {s["employee_id"]: s for s in run["payslips"]}
omar = slips[second_id]
assert omar["late_penalty_days"] == 0.5, f"4 lates should cost one 0.5-day penalty, got {omar['late_penalty_days']}"
print(f"OK 4 lates -> {omar['late_penalty_days']} day penalty (partial groups ignored)")

jane_slip = slips[employee_id]
assert jane_slip["late_penalty_days"] == 0, jane_slip["late_penalty_days"]
print("OK an employee with no lates gets no penalty")

# Two more lates take Omar to six -> the penalty must double.
db = SessionLocal()
for day in (14, 15):
    db.add(_Attendance(employee_id=second_id, date=_date(2026, 10, day), status="late", source="web"))
db.commit()
db.close()

run = check("payroll recomputed", client.post("/payroll/runs", headers=hr_headers, json={"month": 10, "year": 2026}))
omar = {s["employee_id"]: s for s in run["payslips"]}[second_id]
assert omar["late_penalty_days"] == 1.0, f"6 lates should cost 1.0 day, got {omar['late_penalty_days']}"
print("OK 6 lates -> 1.0 day penalty")

# 34. Insights: attrition risk and absence anomalies
ins = check("insights", client.get("/dashboards/insights", headers=hr_headers))
for key in ("attrition_risk", "absence_anomalies", "late_penalty", "as_of"):
    assert key in ins, f"insights missing {key}"
assert ins["late_penalty"] == {"lates_per_penalty": 3, "penalty_days": 0.5}, ins["late_penalty"]

flagged = {a["name"]: a for a in ins["absence_anomalies"]}
assert "Omar Siddiqui" in flagged, f"6 lates should raise a flag: {list(flagged)}"
assert any(f["flag"] == "frequent_late" for f in flagged["Omar Siddiqui"]["flags"]), flagged["Omar Siddiqui"]
print(f"OK absence anomalies flagged {len(ins['absence_anomalies'])} employee(s)")

risky = {r["name"]: r for r in ins["attrition_risk"]}
assert all(0 < r["score"] <= 100 for r in risky.values()), risky
assert all(len(r["factors"]) > 0 for r in risky.values()), "every score must explain itself"
assert all(r["band"] in ("low", "medium", "high") for r in risky.values()), risky
print(f"OK attrition risk scored {len(risky)} employee(s), each with its reasons")

r = client.get("/dashboards/insights", headers=emp_headers)
assert r.status_code == 403, r.text
print("OK insights are Admin/HR only (employee 403)")

# 35. Filters, pagination and CSV exports on the data tables
emps = check("employees paged", client.get("/employees", headers=hr_headers, params={"page": 1, "page_size": 1}))
assert len(emps["items"]) == 1 and emps["total"] >= 2, emps
page2 = check("employees page 2", client.get("/employees", headers=hr_headers, params={"page": 2, "page_size": 1}))
assert page2["items"][0]["id"] != emps["items"][0]["id"], "page 2 returned the same row as page 1"
print(f"OK employees paginate ({emps['total']} total, 1 per page)")

by_dept = check("employees by department", client.get("/employees", headers=hr_headers, params={"department_id": dept_id}))
assert by_dept["total"] >= 2, by_dept
empty = check("employees in a dept with nobody", client.get("/employees", headers=hr_headers, params={"department_id": dept_id + 999}))
assert empty["total"] == 0, empty
named = check("employee search", client.get("/employees", headers=hr_headers, params={"search": "Omar"}))
assert named["total"] == 1 and named["items"][0]["full_name"] == "Omar Siddiqui", named
print("OK employee search and department filters narrow results")

approved = check("leave filtered by status", client.get("/leave", headers=admin_headers, params={"status": "approved"}))
assert all(r["status"] == "approved" for r in approved["items"]), approved
none_pending = check("leave filtered to pending", client.get("/leave", headers=admin_headers, params={"status": "pending"}))
assert none_pending["total"] == 0, none_pending
ranged = check("leave filtered by date", client.get("/leave", headers=admin_headers, params={"start": "2026-11-01", "end": "2026-11-30"}))
assert ranged["total"] == 1, ranged
outside = check("leave outside the range", client.get("/leave", headers=admin_headers, params={"start": "2026-01-01", "end": "2026-01-31"}))
assert outside["total"] == 0, outside
print("OK leave filters by status and overlapping date range")

board_all = check("board unfiltered", client.get("/attendance/board", headers=hr_headers, params={"day": "2026-10-07"}))
board_one = check("board filtered by name", client.get("/attendance/board", headers=hr_headers, params={"day": "2026-10-07", "search": "Omar"}))
assert len(board_all) > len(board_one) and len(board_one) == 1, (len(board_all), len(board_one))
board_absent = check("board filtered by status", client.get("/attendance/board", headers=hr_headers, params={"day": "2026-10-07", "status": "absent"}))
assert all(r["status"] == "absent" for r in board_absent), board_absent
print("OK attendance board filters by search and status")

audit = check("audit paged", client.get("/audit-log", headers=admin_headers, params={"page_size": 5}))
assert len(audit["items"]) <= 5 and audit["total"] > 5, audit
opts = check("audit filter options", client.get("/audit-log/filters", headers=admin_headers))
assert "create" in opts["actions"] and "employee" in opts["entities"], opts
only_finalize = check("audit filtered", client.get("/audit-log", headers=admin_headers, params={"action": "finalize"}))
assert only_finalize["total"] >= 1 and all(r["action"] == "finalize" for r in only_finalize["items"]), only_finalize
print(f"OK audit log pages and filters ({audit['total']} entries, actions: {opts['actions']})")

# CSV exports return real CSV with the filters applied, and stay role-scoped.
csv_emp = client.get("/employees/export-csv", headers=hr_headers)
assert csv_emp.status_code == 200 and "code,full_name" in csv_emp.text, csv_emp.text[:120]
csv_leave = client.get("/leave/export-csv", headers=admin_headers)
assert csv_leave.status_code == 200 and "employee_code,employee,type" in csv_leave.text, csv_leave.text[:120]
assert "Jane Doe" in csv_leave.text, csv_leave.text[:200]
csv_att = client.get("/attendance/board/export-csv", headers=hr_headers, params={"day": "2026-10-07"})
assert csv_att.status_code == 200 and "date,employee_code" in csv_att.text, csv_att.text[:120]
csv_audit = client.get("/audit-log/export-csv", headers=admin_headers)
assert csv_audit.status_code == 200 and "when,actor_id,action" in csv_audit.text, csv_audit.text[:120]
csv_pay = client.get(f"/payroll/runs/{run_id}/export-csv", headers=hr_headers)
assert csv_pay.status_code == 200 and "late_penalty_days" in csv_pay.text, csv_pay.text[:160]
print("OK CSV exports for employees, leave, attendance, audit and payroll")

for path in ("/leave/export-csv", "/attendance/board/export-csv"):
    r = client.get(path, headers=emp_headers)
    assert r.status_code == 403, f"{path} should be staff-only, got {r.status_code}"
r = client.get("/audit-log/export-csv", headers=hr_headers)
assert r.status_code == 403, r.text
print("OK exports respect roles (employee blocked, audit export Admin-only)")

# 36. Employee self-service filters
mine_year = check("my leave by year", client.get("/leave/mine", headers=emp_headers, params={"year": 2026}))
assert len(mine_year) >= 1, mine_year
mine_other = check("my leave, different year", client.get("/leave/mine", headers=emp_headers, params={"year": 2020}))
assert mine_other == [], mine_other
slips_year = check("my payslips by year", client.get("/payroll/payslips/mine", headers=emp_headers, params={"year": 2020}))
assert slips_year == [], slips_year
print("OK employee leave and payslip filters work on their own data")

# 37. Reports — each role sees only its own, and the numbers match the records
staff_reports = check("reports list (HR)", client.get("/reports", headers=hr_headers))["reports"]
staff_keys = {r["key"] for r in staff_reports}
assert staff_keys == {"attendance-register", "leave-register", "late-comers", "payroll-register", "headcount"}, staff_keys

emp_reports = check("reports list (employee)", client.get("/reports", headers=emp_headers))["reports"]
emp_keys = {r["key"] for r in emp_reports}
assert emp_keys == {"my-attendance", "my-leave", "my-payslips"}, emp_keys
print(f"OK reports are role-scoped: staff {len(staff_keys)}, employee {len(emp_keys)}")

# An employee must not be able to run a staff report by guessing its name.
r = client.get("/reports/attendance-register", headers=emp_headers)
assert r.status_code == 403, r.text
r = client.get("/reports/payroll-register/export-csv", headers=emp_headers)
assert r.status_code == 403, r.text
# ...and staff cannot run the self-scoped ones, which have no employee to scope to.
r = client.get("/reports/my-payslips", headers=hr_headers)
assert r.status_code == 403, r.text
print("OK reports refuse the wrong role, including the CSV route")

r = client.get("/reports/not-a-report", headers=hr_headers)
assert r.status_code == 404, r.text

# Attendance register over the window we know: Jane present+half, Omar 6 lates.
reg = check(
    "attendance register",
    client.get("/reports/attendance-register", headers=hr_headers, params={"start": "2026-10-01", "end": "2026-10-20"}),
)
assert {c["key"] for c in reg["columns"]} >= {"employee", "present", "late", "absent", "attendance_rate"}, reg["columns"]
rows = {r["employee"]: r for r in reg["rows"]}
assert rows["Omar Siddiqui"]["late"] == 6, rows["Omar Siddiqui"]
assert reg["totals"]["late"] == 6, reg["totals"]
assert 0 <= reg["totals"]["attendance_rate"] <= 100, reg["totals"]
print(f"OK attendance register: Omar {rows['Omar Siddiqui']['late']} lates, overall rate {reg['totals']['attendance_rate']}%")

late = check("late-comers report", client.get("/reports/late-comers", headers=hr_headers, params={"start": "2026-10-01", "end": "2026-10-20"}))
assert late["rows"][0]["employee"] == "Omar Siddiqui" and late["rows"][0]["penalty_days"] == 1.0, late["rows"]
print("OK late-comers report matches the payroll penalty (6 lates -> 1.0 day)")

leave_reg = check("leave register", client.get("/reports/leave-register", headers=hr_headers, params={"start": "2026-11-01", "end": "2026-11-30"}))
assert leave_reg["totals"]["total"] == 2.0, leave_reg["totals"]
print("OK leave register totals the approved days")

head = check("headcount report", client.get("/reports/headcount", headers=hr_headers, params={"start": "2026-01-01", "end": "2026-12-31"}))
assert head["totals"]["headcount"] >= 2 and head["totals"]["joiners"] >= 2, head["totals"]
print(f"OK headcount report: {head['totals']['headcount']} active, {head['totals']['joiners']} joined")

pay = check("payroll register", client.get("/reports/payroll-register", headers=hr_headers, params={"month": 10, "year": 2026}))
assert len(pay["rows"]) >= 1 and "net_pay" in pay["totals"], pay
missing = check("payroll register, month with no run", client.get("/reports/payroll-register", headers=hr_headers, params={"month": 7, "year": 2026}))
assert missing["rows"] == [] and "No payroll run" in missing["subtitle"], missing
print("OK payroll register reports a month with no run instead of failing")

# Employee reports stay on their own data.
mine = check("my leave statement", client.get("/reports/my-leave", headers=emp_headers, params={"year": 2026}))
assert mine["totals"]["used"] == 2.0, mine["totals"]
mine_att = check("my attendance report", client.get("/reports/my-attendance", headers=emp_headers, params={"start": "2026-10-01", "end": "2026-10-10"}))
assert len(mine_att["rows"]) > 0 and {"date", "status"} == {c["key"] for c in mine_att["columns"]}, mine_att["columns"]
print("OK employee reports return only their own records")

csv_report = client.get("/reports/attendance-register/export-csv", headers=hr_headers, params={"start": "2026-10-01", "end": "2026-10-20"})
assert csv_report.status_code == 200 and "Employee,Code,Department" in csv_report.text, csv_report.text[:150]
assert "Omar Siddiqui" in csv_report.text, csv_report.text[:300]
print("OK report CSV export carries the same rows")

# 38. The follow-up request after a tool call must carry only defined fields.
# OpenAI ignores stray nulls like function_call/refusal; stricter OpenAI-compatible
# providers (Groq among them) reject them with a 400, which broke every question
# that needed a tool while plain chat kept working.
from app.ai import client as ai_client

sent_messages = {}


class _StubFn:
    def __init__(self):
        self.name = "get_headcount"
        self.arguments = "{}"


class _StubCall:
    def __init__(self):
        self.id = "call_1"
        self.type = "function"
        self.function = _StubFn()


class _StubMessage:
    def __init__(self, tool_calls=None, content=None):
        self.tool_calls = tool_calls
        self.content = content

    def model_dump(self):  # what the old code used — deliberately noisy
        return {"role": "assistant", "content": self.content, "function_call": None, "refusal": None, "audio": None}


class _StubCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, model, messages, tools):
        self.calls += 1
        sent_messages[self.calls] = [dict(m) for m in messages]
        if self.calls == 1:
            return type("R", (), {"choices": [type("C", (), {"message": _StubMessage(tool_calls=[_StubCall()])})()]})()
        return type("R", (), {"choices": [type("C", (), {"message": _StubMessage(content="There are 2 active employees.")})()]})()


class _StubClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _StubCompletions()})()


ai_client._openai_client = lambda: _StubClient()
_previous_provider = ai_client.settings.ai_provider
ai_client.settings.ai_provider = "openai"

answer, tool_log = ai_client.chat_with_tools(SessionLocal(), hr_user, "system prompt", "How many employees?")
ai_client.settings.ai_provider = _previous_provider

assert answer == "There are 2 active employees.", answer
assert tool_log and tool_log[0]["name"] == "get_headcount", tool_log

follow_up = sent_messages[2]
assistant = next(m for m in follow_up if m["role"] == "assistant")
assert set(assistant) == {"role", "content", "tool_calls"}, f"stray fields would 400 on Groq: {sorted(assistant)}"
assert assistant["content"] is not None, "null content is rejected by some providers"
assert assistant["tool_calls"][0]["function"]["name"] == "get_headcount", assistant["tool_calls"]

tool_reply = next(m for m in follow_up if m["role"] == "tool")
assert tool_reply["tool_call_id"] == "call_1", tool_reply
print("OK the tool-call follow-up sends only role/content/tool_calls, with the tool result attached")

print("\nALL SMOKE TESTS PASSED")
