"""One-off seed script to populate a fresh local database with realistic, clean
demo data purely for capturing landing-page screenshots. Not part of the app,
never deployed — the product itself always starts empty, per the brief.

Run from anywhere:   python backend/scripts/seed_demo.py
It overwrites backend/dev.db. Back up anything in it you want to keep first —
for example, swap it aside (`mv dev.db dev.db.bak`) and swap it back after.
"""
import os
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = BACKEND_ROOT / "dev.db"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "demo-seed-secret"
os.environ["AI_API_KEY"] = ""
sys.path.insert(0, str(BACKEND_ROOT))

if DB_PATH.exists():
    DB_PATH.unlink()

random.seed(7)

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest
from app.models.org import LeaveType
from app.services import auth_service, employee_service, leave_service, org_service, payroll_service

Base.metadata.create_all(bind=engine)
db = SessionLocal()

today = date.today()

# --- company + admin --------------------------------------------------------
admin = auth_service.first_run_setup(db, "BrightPath Retail Co", "admin@brightpath.demo", "BrightAdmin#2026")
org_service.seed_default_leave_types(db, admin.id)
org_service.update_settings(db, admin.id, {
    "timezone": "Asia/Karachi",
    "office_lat": 24.8607,
    "office_lng": 67.0011,
    "office_radius_m": 200,
})
settings = org_service.get_settings(db)

departments = {name: org_service.create_department(db, admin.id, name) for name in
               ["Engineering", "Sales", "Operations", "Customer Support"]}
designations = {name: org_service.create_designation(db, admin.id, name) for name in
                ["Software Engineer", "Sales Executive", "Team Lead", "Operations Analyst", "Support Specialist"]}

holiday_date = today.replace(day=1) - timedelta(days=20)
while holiday_date.weekday() >= 5:
    holiday_date += timedelta(days=1)
org_service.create_holiday(db, admin.id, holiday_date, "Company Foundation Day")

hr = auth_service.create_hr_user(db, admin.id, "Imran Qureshi", "hr@brightpath.demo", "BrightHR#2026", require_password_change=False)

# --- employees ---------------------------------------------------------------
EMPLOYEES = [
    # code, name, email, dept, designation, salary, gender, months_tenure, attendance_quality
    ("ENG001", "Ayesha Khan", "ayesha.khan@brightpath.demo", "Engineering", "Software Engineer", 145000, "Female", 20, "good"),
    ("ENG002", "Bilal Ahmed", "bilal.ahmed@brightpath.demo", "Engineering", "Software Engineer", 132000, "Male", 14, "good"),
    ("SAL001", "Sara Malik", "sara.malik@brightpath.demo", "Sales", "Sales Executive", 95000, "Female", 9, "good"),
    ("SAL002", "Hassan Raza", "hassan.raza@brightpath.demo", "Sales", "Team Lead", 118000, "Male", 26, "weak"),
    ("OPS001", "Fatima Noor", "fatima.noor@brightpath.demo", "Operations", "Operations Analyst", 88000, "Female", 5, "good"),
    ("OPS002", "Usman Tariq", "usman.tariq@brightpath.demo", "Operations", "Operations Analyst", 91000, "Male", 11, "good"),
    ("SUP001", "Zainab Sheikh", "zainab.sheikh@brightpath.demo", "Customer Support", "Support Specialist", 76000, "Female", 3, "average"),
    ("SUP002", "Ahmed Siddiqui", "ahmed.siddiqui@brightpath.demo", "Customer Support", "Support Specialist", 79000, "Male", 15, "good"),
]

employees = {}
temp_passwords = {}
for code, name, email, dept, desig, salary, gender, months, quality in EMPLOYEES:
    joined = today - timedelta(days=months * 30 + random.randint(0, 20))
    emp, temp_pw = employee_service.register_employee(db, hr.id, {
        "code": code, "full_name": name, "email": email,
        "department_id": departments[dept].id, "designation_id": designations[desig].id,
        "date_of_joining": joined, "basic_salary": salary, "gender": gender,
        "phone": f"0300-{random.randint(1000000, 9999999)}",
    })
    employees[code] = (emp, quality)
    temp_passwords[email] = temp_pw
    # give every employee a usable fixed password for screenshot logins
    emp.user.password_hash = hash_password("Demo#2026")
    emp.user.must_change_password = False
    db.commit()

QUALITY_WEIGHTS = {
    "good": {"present": 0.84, "late": 0.08, "half_day": 0.02, "absent": 0.06},
    "average": {"present": 0.74, "late": 0.14, "half_day": 0.03, "absent": 0.09},
    "weak": {"present": 0.55, "late": 0.30, "half_day": 0.03, "absent": 0.12},
}

prev_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
# Insights looks back 90 days; seed at least that far so nobody shows a false
# "absent" streak just because there is no attendance row before the window.
window_start = min(prev_month_start, today - timedelta(days=100))
holidays = {holiday_date}

KARACHI_OFFSET = timedelta(hours=5)


def stamp(d: date, hh: int, mm: int) -> datetime:
    return datetime.combine(d, time(hh, mm)) - KARACHI_OFFSET  # store as UTC


day = window_start
while day <= today:
    is_weekend = day.weekday() >= 5
    is_holiday = day in holidays
    if not is_weekend and not is_holiday:
        for code, (emp, quality) in employees.items():
            weights = QUALITY_WEIGHTS[quality]
            roll = random.random()
            cum = 0.0
            status = "present"
            for key, weight in weights.items():
                cum += weight
                if roll <= cum:
                    status = key
                    break
            if status == "absent":
                continue  # no row -> derived as absent
            check_in_hh, check_in_mm = (8, random.randint(45, 59)) if status == "present" else (9, random.randint(20, 55))
            row = Attendance(
                employee_id=emp.id, date=day, status=status, source="web",
                check_in_time=stamp(day, check_in_hh, check_in_mm),
            )
            if status == "half_day":
                row.check_out_time = stamp(day, 13, random.randint(0, 30))
            elif status != "missing_checkout":
                row.check_out_time = stamp(day, 18, random.randint(0, 25))
            db.add(row)
    day += timedelta(days=1)
db.commit()

# --- leave ---------------------------------------------------------------
leave_types = {lt.name: lt for lt in db.query(LeaveType).all()}

ayesha = employees["ENG001"][0]
sara = employees["SAL001"][0]
usman = employees["OPS002"][0]
zainab = employees["SUP001"][0]

approved_1 = leave_service.apply_leave(db, settings, ayesha, leave_types["annual"].id, today - timedelta(days=18), today - timedelta(days=16), "Family trip")
leave_service.decide_leave(db, hr.id, approved_1, True, "Enjoy!")

approved_2 = leave_service.apply_leave(db, settings, usman, leave_types["sick"].id, today - timedelta(days=6), today - timedelta(days=6), "Fever")
leave_service.decide_leave(db, hr.id, approved_2, True, "Get well soon")

approved_3 = leave_service.apply_leave(db, settings, zainab, leave_types["casual"].id, today - timedelta(days=4), today - timedelta(days=3), "Personal errand")
leave_service.decide_leave(db, hr.id, approved_3, True, None)

# Any Attendance row already seeded for an approved-leave day would hide the leave
# (an explicit record wins over a leave inference), so clear those days.
for approved in (approved_1, approved_2, approved_3):
    db.query(Attendance).filter(
        Attendance.employee_id == approved.employee_id,
        Attendance.date >= approved.start_date,
        Attendance.date <= approved.end_date,
    ).delete()
db.commit()

# one pending, for the approvals inbox screenshot
next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
leave_service.apply_leave(db, settings, sara, leave_types["annual"].id, next_monday, next_monday + timedelta(days=1), "Cousin's wedding")

# --- payroll: finalize last month ----------------------------------------
run = payroll_service.create_or_refresh_draft(db, hr.id, settings, prev_month_start.month, prev_month_start.year)
payroll_service.finalize_run(db, admin.id, run)

db.close()
print("Seeded demo database:", DB_PATH)
print("Admin login: admin@brightpath.demo / BrightAdmin#2026")
print("HR login:    hr@brightpath.demo / BrightHR#2026")
print("Employee logins use the temporary passwords printed during registration (see register_employee calls above) —")
print("for screenshots, log in via the API using Ayesha Khan:", "ayesha.khan@brightpath.demo")
