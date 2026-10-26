"""Reports: period summaries over the records already in the system.

Every report returns the same shape — columns, rows, optional totals — so one
screen renders all of them and one endpoint exports any of them as CSV. Adding a
report means adding a builder and an entry in REPORTS, nothing else.
"""

import calendar
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.org import CompanySettings, Department, LeaveType
from app.models.payroll import PayrollRun, Payslip
from app.services.insights import _day_statuses
from app.services.payroll_service import LATES_PER_PENALTY, PENALTY_DAYS

WORKED = ("present", "late", "half_day", "missing_checkout")
CREDIT = {"present": 1.0, "late": 1.0, "missing_checkout": 1.0, "half_day": 0.5, "absent": 0.0}


def _col(key: str, label: str, numeric: bool = False) -> dict:
    return {"key": key, "label": label, "numeric": numeric}


def _employees(db: Session, department_id: int | None, include_exited: bool = False) -> list[Employee]:
    query = db.query(Employee)
    if not include_exited:
        query = query.filter(Employee.status.in_(["active", "probation"]))
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    return query.order_by(Employee.full_name).all()


def _dept_label(db: Session, department_id: int | None) -> str:
    if not department_id:
        return "All departments"
    dept = db.get(Department, department_id)
    return dept.name if dept else "Unknown department"


def _month_bounds(month: int, year: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


# --- staff reports ---------------------------------------------------------


def attendance_register(db, settings, *, start, end, department_id=None, **_):
    employees = _employees(db, department_id)
    statuses, working_days = _day_statuses(db, settings, employees, start, end)

    rows, totals = [], {"working_days": 0, "present": 0, "late": 0, "half_day": 0, "on_leave": 0, "absent": 0}
    credit_sum = expected_sum = 0.0

    for employee in employees:
        per_day = statuses.get(employee.id, {})
        if not per_day:
            continue
        counts = {k: 0 for k in ("present", "late", "half_day", "missing_checkout", "on_leave", "absent")}
        for value in per_day.values():
            counts[value] = counts.get(value, 0) + 1

        expected = len(per_day) - counts["on_leave"]
        credit = sum(CREDIT.get(v, 0.0) for v in per_day.values() if v != "on_leave")
        credit_sum += credit
        expected_sum += expected

        rows.append({
            "employee": employee.full_name,
            "code": employee.code,
            "department": employee.department.name if employee.department else "—",
            "working_days": len(per_day),
            "present": counts["present"],
            "late": counts["late"],
            "half_day": counts["half_day"],
            "on_leave": counts["on_leave"],
            "absent": counts["absent"],
            "attendance_rate": round((credit / expected) * 100, 1) if expected else 0.0,
        })
        for key in totals:
            totals[key] += rows[-1][key]

    totals["attendance_rate"] = round((credit_sum / expected_sum) * 100, 1) if expected_sum else 0.0
    totals["employee"] = f"{len(rows)} employees"

    return {
        "title": "Attendance register",
        "subtitle": f"{start} to {end} · {_dept_label(db, department_id)} · {len(working_days)} working days",
        "columns": [
            _col("employee", "Employee"), _col("code", "Code"), _col("department", "Department"),
            _col("working_days", "Working days", True), _col("present", "Present", True),
            _col("late", "Late", True), _col("half_day", "Half days", True),
            _col("on_leave", "On leave", True), _col("absent", "Absent", True),
            _col("attendance_rate", "Attendance %", True),
        ],
        "rows": rows,
        "totals": totals,
    }


def leave_register(db, settings, *, start, end, department_id=None, **_):
    employees = _employees(db, department_id)
    leave_types = db.query(LeaveType).order_by(LeaveType.name).all()
    by_employee = {e.id: {lt.name: 0.0 for lt in leave_types} for e in employees}

    requests = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.status == "approved",
            LeaveRequest.employee_id.in_([e.id for e in employees] or [0]),
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .all()
    )
    for request in requests:
        name = request.leave_type_name
        if name in by_employee.get(request.employee_id, {}):
            by_employee[request.employee_id][name] += request.days

    rows, totals = [], {lt.name: 0.0 for lt in leave_types}
    totals["total"] = 0.0
    for employee in employees:
        per_type = by_employee[employee.id]
        total = sum(per_type.values())
        if total == 0:
            continue
        row = {"employee": employee.full_name, "code": employee.code,
               "department": employee.department.name if employee.department else "—", **per_type, "total": total}
        rows.append(row)
        for name in per_type:
            totals[name] += per_type[name]
        totals["total"] += total
    totals["employee"] = f"{len(rows)} employees"

    return {
        "title": "Leave register",
        "subtitle": f"Approved leave {start} to {end} · {_dept_label(db, department_id)}",
        "columns": [
            _col("employee", "Employee"), _col("code", "Code"), _col("department", "Department"),
            *[_col(lt.name, lt.name.title(), True) for lt in leave_types],
            _col("total", "Total days", True),
        ],
        "rows": rows,
        "totals": totals,
    }


def payroll_register(db, settings, *, month, year, department_id=None, **_):
    run = db.query(PayrollRun).filter(PayrollRun.month == month, PayrollRun.year == year).first()
    if run is None:
        return {
            "title": "Payroll register",
            "subtitle": f"No payroll run exists for {month:02d}/{year}",
            "columns": [_col("employee", "Employee")],
            "rows": [],
            "totals": None,
        }

    query = db.query(Payslip).join(Employee, Payslip.employee_id == Employee.id).filter(Payslip.payroll_run_id == run.id)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    slips = query.order_by(Employee.full_name).all()

    rows, totals = [], {k: 0.0 for k in ("gross", "deductions", "late_penalty_days", "tax", "net_pay")}
    for slip in slips:
        row = {
            "employee": slip.employee_name or "—",
            "code": slip.employee_code or "—",
            "gross": round(slip.gross, 2),
            "deductions": round(slip.deductions, 2),
            "late_penalty_days": slip.late_penalty_days or 0,
            "tax": round(slip.tax, 2),
            "net_pay": round(slip.net_pay, 2),
        }
        rows.append(row)
        for key in totals:
            totals[key] += row[key]
    totals = {k: round(v, 2) for k, v in totals.items()}
    totals["employee"] = f"{len(rows)} employees"

    return {
        "title": "Payroll register",
        "subtitle": f"{month:02d}/{year} · {run.status} · {_dept_label(db, department_id)}",
        "columns": [
            _col("employee", "Employee"), _col("code", "Code"), _col("gross", "Gross", True),
            _col("late_penalty_days", "Late penalty (days)", True), _col("deductions", "Deductions", True),
            _col("tax", "Tax", True), _col("net_pay", "Net pay", True),
        ],
        "rows": rows,
        "totals": totals,
    }


def headcount_report(db, settings, *, start, end, department_id=None, **_):
    departments = db.query(Department).order_by(Department.name).all()
    buckets = {d.id: d.name for d in departments}
    buckets[None] = "Unassigned"

    rows, totals = [], {"headcount": 0, "joiners": 0, "leavers": 0}
    for dept_id, name in buckets.items():
        if department_id and dept_id != department_id:
            continue
        everyone = db.query(Employee).filter(Employee.department_id == dept_id).all()
        active = [e for e in everyone if e.status in ("active", "probation")]
        joiners = [e for e in everyone if start <= e.date_of_joining <= end]
        leavers = [e for e in everyone if e.date_of_leaving and start <= e.date_of_leaving <= end]
        if not everyone:
            continue

        average = len(active) + len(leavers) / 2
        rows.append({
            "department": name,
            "headcount": len(active),
            "joiners": len(joiners),
            "leavers": len(leavers),
            "attrition_pct": round((len(leavers) / average) * 100, 1) if average else 0.0,
        })
        totals["headcount"] += len(active)
        totals["joiners"] += len(joiners)
        totals["leavers"] += len(leavers)

    average_total = totals["headcount"] + totals["leavers"] / 2
    totals["attrition_pct"] = round((totals["leavers"] / average_total) * 100, 1) if average_total else 0.0
    totals["department"] = f"{len(rows)} departments"

    return {
        "title": "Headcount and attrition",
        "subtitle": f"Joiners and leavers between {start} and {end}",
        "columns": [
            _col("department", "Department"), _col("headcount", "Headcount", True),
            _col("joiners", "Joined", True), _col("leavers", "Left", True), _col("attrition_pct", "Attrition %", True),
        ],
        "rows": rows,
        "totals": totals,
    }


def late_comers(db, settings, *, start, end, department_id=None, **_):
    employees = _employees(db, department_id)
    statuses, _unused = _day_statuses(db, settings, employees, start, end)

    rows, totals = [], {"late": 0, "penalty_days": 0.0}
    for employee in employees:
        late = sum(1 for v in statuses.get(employee.id, {}).values() if v == "late")
        if late == 0:
            continue
        penalty = (late // LATES_PER_PENALTY) * PENALTY_DAYS
        rows.append({
            "employee": employee.full_name,
            "code": employee.code,
            "department": employee.department.name if employee.department else "—",
            "late": late,
            "penalty_days": penalty,
        })
        totals["late"] += late
        totals["penalty_days"] += penalty

    rows.sort(key=lambda r: r["late"], reverse=True)
    totals["employee"] = f"{len(rows)} employees"

    return {
        "title": "Late arrivals",
        "subtitle": f"{start} to {end} · {LATES_PER_PENALTY} lates cost {PENALTY_DAYS} of a day",
        "columns": [
            _col("employee", "Employee"), _col("code", "Code"), _col("department", "Department"),
            _col("late", "Late arrivals", True), _col("penalty_days", "Penalty (days)", True),
        ],
        "rows": rows,
        "totals": totals,
    }


# --- employee reports (always scoped to the caller) ------------------------


def my_attendance(db, settings, *, employee, start, end, **_):
    statuses, _unused = _day_statuses(db, settings, [employee], start, end)
    per_day = statuses.get(employee.id, {})

    rows = [{"date": str(day), "status": value.replace("_", " ")} for day, value in sorted(per_day.items())]
    counts: dict[str, int] = {}
    for value in per_day.values():
        counts[value] = counts.get(value, 0) + 1
    summary = " · ".join(f"{v} {k.replace('_', ' ')}" for k, v in sorted(counts.items())) or "no working days"

    return {
        "title": "My attendance",
        "subtitle": f"{start} to {end} — {summary}",
        "columns": [_col("date", "Date"), _col("status", "Status")],
        "rows": rows,
        "totals": None,
    }


def my_leave_statement(db, settings, *, employee, year, **_):
    leave_types = db.query(LeaveType).order_by(LeaveType.name).all()
    rows, totals = [], {"used": 0.0}

    for leave_type in leave_types:
        used = sum(
            r.days
            for r in db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.leave_type_id == leave_type.id,
                LeaveRequest.status == "approved",
            )
            if r.start_date.year == year
        )
        rows.append({
            "type": leave_type.name.title(),
            "quota": leave_type.annual_quota if leave_type.annual_quota is not None else "unlimited",
            "used": used,
            "remaining": (leave_type.annual_quota - used) if leave_type.annual_quota is not None else "unlimited",
        })
        totals["used"] += used
    totals["type"] = f"{len(rows)} leave types"

    return {
        "title": "My leave statement",
        "subtitle": f"Approved leave in {year}",
        "columns": [_col("type", "Leave type"), _col("quota", "Quota"), _col("used", "Used", True), _col("remaining", "Remaining")],
        "rows": rows,
        "totals": totals,
    }


def my_payslips(db, settings, *, employee, year, **_):
    query = (
        db.query(Payslip)
        .join(PayrollRun)
        .filter(Payslip.employee_id == employee.id, PayrollRun.status == "finalized")
    )
    if year:
        query = query.filter(PayrollRun.year == year)
    slips = query.order_by(PayrollRun.year.desc(), PayrollRun.month.desc()).all()

    rows, totals = [], {k: 0.0 for k in ("gross", "deductions", "tax", "net_pay")}
    for slip in slips:
        row = {
            "period": f"{slip.payroll_run.month:02d}/{slip.payroll_run.year}",
            "gross": round(slip.gross, 2),
            "deductions": round(slip.deductions, 2),
            "tax": round(slip.tax, 2),
            "net_pay": round(slip.net_pay, 2),
        }
        rows.append(row)
        for key in totals:
            totals[key] += row[key]
    totals = {k: round(v, 2) for k, v in totals.items()}
    totals["period"] = f"{len(rows)} payslips"

    return {
        "title": "My payslip history",
        "subtitle": f"Finalized payslips in {year}",
        "columns": [
            _col("period", "Period"), _col("gross", "Gross", True), _col("deductions", "Deductions", True),
            _col("tax", "Tax", True), _col("net_pay", "Net pay", True),
        ],
        "rows": rows,
        "totals": totals,
    }


# --- registry --------------------------------------------------------------

REPORTS = {
    "attendance-register": {
        "builder": attendance_register, "roles": ("admin", "hr"), "params": ["range", "department"],
        "title": "Attendance register",
        "description": "Present, late, half days, leave and absence per employee, with the attendance rate.",
    },
    "leave-register": {
        "builder": leave_register, "roles": ("admin", "hr"), "params": ["range", "department"],
        "title": "Leave register",
        "description": "Approved leave days per employee, broken down by leave type.",
    },
    "late-comers": {
        "builder": late_comers, "roles": ("admin", "hr"), "params": ["range", "department"],
        "title": "Late arrivals",
        "description": "Who arrived late, how often, and the resulting pay penalty.",
    },
    "payroll-register": {
        "builder": payroll_register, "roles": ("admin", "hr"), "params": ["month", "department"],
        "title": "Payroll register",
        "description": "Gross, deductions, tax and net pay for every employee in one month.",
    },
    "headcount": {
        "builder": headcount_report, "roles": ("admin", "hr"), "params": ["range", "department"],
        "title": "Headcount and attrition",
        "description": "Headcount, joiners and leavers by department, with attrition.",
    },
    "my-attendance": {
        "builder": my_attendance, "roles": ("employee",), "params": ["range"], "self": True,
        "title": "My attendance",
        "description": "Every working day in the period and how it was recorded.",
    },
    "my-leave": {
        "builder": my_leave_statement, "roles": ("employee",), "params": ["year"], "self": True,
        "title": "My leave statement",
        "description": "Leave used against quota for each type this year.",
    },
    "my-payslips": {
        "builder": my_payslips, "roles": ("employee",), "params": ["year"], "self": True,
        "title": "My payslip history",
        "description": "Finalized payslips with gross, deductions and net pay.",
    },
}


def available(role: str) -> list[dict]:
    return [
        {"key": key, "title": spec["title"], "description": spec["description"], "params": spec["params"]}
        for key, spec in REPORTS.items()
        if role in spec["roles"]
    ]


def run(db: Session, settings: CompanySettings, key: str, role: str, employee: Employee | None, params: dict) -> dict:
    spec = REPORTS.get(key)
    if spec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown report")
    if role not in spec["roles"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This report is not available for your role")
    if spec.get("self"):
        if employee is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record for this account")
        params = {**params, "employee": employee}

    report = spec["builder"](db, settings, **params)
    report["key"] = key
    return report


def to_csv(report: dict) -> str:
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([c["label"] for c in report["columns"]])
    for row in report["rows"]:
        writer.writerow([row.get(c["key"], "") for c in report["columns"]])
    if report.get("totals"):
        writer.writerow([report["totals"].get(c["key"], "") for c in report["columns"]])
    return buffer.getvalue()
