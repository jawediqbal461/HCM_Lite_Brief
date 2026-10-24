from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.comms import AuditLog
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.org import CompanySettings, Department, Holiday, LeaveType
from app.models.payroll import Payslip, PayrollRun
from app.core.clock import business_today
from app.services.attendance_service import is_weekend

# Weight each day contributes to the attendance rate numerator (brief, Section 7):
# (present + late + missing_checkout + 0.5 x half_day) / (working-day records - on_leave)
ATTENDANCE_CREDIT = {
    "present": 1.0,
    "late": 1.0,
    "missing_checkout": 1.0,
    "half_day": 0.5,
    "absent": 0.0,
}


def _date_range_defaults(start: date | None, end: date | None) -> tuple[date, date]:
    end = end or date.today()
    start = start or (end - timedelta(days=30))
    return start, end


def _company_settings(db: Session) -> CompanySettings | None:
    return db.query(CompanySettings).first()


def _working_days(db: Session, settings: CompanySettings, start: date, end: date) -> list[date]:
    holidays = {h.date for h in db.query(Holiday).filter(Holiday.date >= start, Holiday.date <= end).all()}
    days = []
    day = start
    while day <= end:
        if not is_weekend(settings, day) and day not in holidays:
            days.append(day)
        day += timedelta(days=1)
    return days


def _active_employees(db: Session, department_id: int | None) -> list[Employee]:
    query = db.query(Employee).filter(Employee.status.in_(["active", "probation"]))
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    return query.all()


def _empty_attendance_stats(start: date, end: date) -> dict:
    return {
        "attendance_rate": 0.0,
        "expected_days": 0,
        "on_leave_days": 0,
        "absent_days": 0,
        "status_counts": {},
        "by_department": [],
        "trend": [],
        "range": {"start": str(start), "end": str(end)},
    }


def attendance_stats(db: Session, start: date, end: date, department_id: int | None = None) -> dict:
    """Attendance rate, absenteeism and a daily trend, computed over expected working days.

    Absent days have no attendance row in this system (rows are only created on check-in or
    a correction request), so the denominator is built from the working days each employee
    was actually employed for, minus days covered by approved leave.
    """
    settings = _company_settings(db)
    if settings is None:
        return _empty_attendance_stats(start, end)

    working_days = _working_days(db, settings, start, end)
    employees = _active_employees(db, department_id)
    if not working_days or not employees:
        return _empty_attendance_stats(start, end)

    working_day_set = set(working_days)
    employee_ids = [e.id for e in employees]

    records = (
        db.query(Attendance)
        .filter(Attendance.employee_id.in_(employee_ids), Attendance.date >= start, Attendance.date <= end)
        .all()
    )
    status_by_day = {(r.employee_id, r.date): r.status for r in records}

    approved_leave = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id.in_(employee_ids),
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .all()
    )
    leave_days: set[tuple[int, date]] = set()
    for leave in approved_leave:
        day = max(leave.start_date, start)
        last = min(leave.end_date, end)
        while day <= last:
            if day in working_day_set:
                leave_days.add((leave.employee_id, day))
            day += timedelta(days=1)

    department_names = {d.id: d.name for d in db.query(Department).all()}
    status_counts: dict[str, int] = {}
    per_department: dict[int | None, dict] = {}
    trend = {day: {"present": 0, "late": 0, "absent": 0, "on_leave": 0} for day in working_days}

    for employee in employees:
        first_day = max(start, employee.date_of_joining)
        last_day = min(end, employee.date_of_leaving) if employee.date_of_leaving else end
        bucket = per_department.setdefault(
            employee.department_id, {"expected": 0, "credit": 0.0, "absent": 0, "on_leave": 0}
        )

        for day in working_days:
            if day < first_day or day > last_day:
                continue

            if (employee.id, day) in leave_days:
                status = "on_leave"
            else:
                status = status_by_day.get((employee.id, day), "absent")
                if status not in ATTENDANCE_CREDIT:
                    status = "present"

            status_counts[status] = status_counts.get(status, 0) + 1

            if status == "on_leave":
                bucket["on_leave"] += 1
                trend[day]["on_leave"] += 1
                continue

            bucket["expected"] += 1
            bucket["credit"] += ATTENDANCE_CREDIT[status]
            if status == "absent":
                bucket["absent"] += 1
                trend[day]["absent"] += 1
            elif status in ("present", "late"):
                trend[day][status] += 1

    expected_days = sum(b["expected"] for b in per_department.values())
    credit = sum(b["credit"] for b in per_department.values())
    absent_days = sum(b["absent"] for b in per_department.values())
    on_leave_days = sum(b["on_leave"] for b in per_department.values())

    by_department = []
    for dept_id, bucket in per_department.items():
        expected = bucket["expected"]
        by_department.append(
            {
                "department_id": dept_id,
                "department": department_names.get(dept_id, "Unassigned"),
                "attendance_rate": round((bucket["credit"] / expected) * 100, 1) if expected else 0.0,
                "absent_days": bucket["absent"],
                "absenteeism_pct": round((bucket["absent"] / expected) * 100, 1) if expected else 0.0,
            }
        )
    by_department.sort(key=lambda row: row["department"])

    return {
        "attendance_rate": round((credit / expected_days) * 100, 1) if expected_days else 0.0,
        "expected_days": expected_days,
        "on_leave_days": on_leave_days,
        "absent_days": absent_days,
        "status_counts": status_counts,
        "by_department": by_department,
        "trend": [{"date": str(day), **values} for day, values in sorted(trend.items())],
        "range": {"start": str(start), "end": str(end)},
    }


def leave_utilization(db: Session, start: date, end: date, department_id: int | None = None) -> list[dict]:
    """Approved leave days against the yearly quota available to the active headcount."""
    headcount = len(_active_employees(db, department_id))
    rows = []
    for leave_type in db.query(LeaveType).order_by(LeaveType.name).all():
        query = (
            db.query(func.coalesce(func.sum(LeaveRequest.days), 0))
            .join(Employee, LeaveRequest.employee_id == Employee.id)
            .filter(
                LeaveRequest.leave_type_id == leave_type.id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date >= start,
                LeaveRequest.start_date <= end,
            )
        )
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        used = float(query.scalar() or 0)
        available = (leave_type.annual_quota or 0) * headcount
        rows.append(
            {
                "type": leave_type.name,
                "days": used,
                "quota_days": available or None,
                "utilization_pct": round((used / available) * 100, 1) if available else None,
            }
        )
    return rows


def admin_dashboard(db: Session, start: date | None, end: date | None, department_id: int | None):
    start, end = _date_range_defaults(start, end)

    emp_query = db.query(Employee)
    if department_id:
        emp_query = emp_query.filter(Employee.department_id == department_id)

    active = emp_query.filter(Employee.status.in_(["active", "probation"])).all()
    headcount = len(active)
    exits = emp_query.filter(
        Employee.status == "exited", Employee.date_of_leaving >= start, Employee.date_of_leaving <= end
    ).count()
    average_headcount = headcount + (exits / 2)
    attrition_pct = round((exits / average_headcount) * 100, 2) if average_headcount else 0.0

    payroll_query = (
        db.query(func.coalesce(func.sum(Payslip.net_pay), 0))
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)
        .join(Employee, Payslip.employee_id == Employee.id)
        .filter(PayrollRun.status == "finalized")
    )
    if department_id:
        payroll_query = payroll_query.filter(Employee.department_id == department_id)
    payroll_cost_total = float(payroll_query.scalar() or 0)

    avg_salary = emp_query.with_entities(func.avg(Employee.basic_salary)).scalar() or 0.0

    department_names = {d.id: d.name for d in db.query(Department).all()}

    headcount_by_department: dict[int | None, int] = {}
    gender_counts: dict[str, int] = {}
    tenure_counts = {"< 1 year": 0, "1-3 years": 0, "3+ years": 0}
    today = date.today()
    for employee in active:
        headcount_by_department[employee.department_id] = headcount_by_department.get(employee.department_id, 0) + 1
        gender_counts[employee.gender or "Not specified"] = gender_counts.get(employee.gender or "Not specified", 0) + 1
        years = (today - employee.date_of_joining).days / 365.25
        bucket = "< 1 year" if years < 1 else ("1-3 years" if years < 3 else "3+ years")
        tenure_counts[bucket] += 1

    cost_by_department = (
        db.query(Employee.department_id, func.coalesce(func.sum(Payslip.net_pay), 0))
        .join(Payslip, Payslip.employee_id == Employee.id)
        .join(PayrollRun, Payslip.payroll_run_id == PayrollRun.id)
        .filter(PayrollRun.status == "finalized")
        .group_by(Employee.department_id)
        .all()
    )

    recent_audit = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(8).all()

    attendance = attendance_stats(db, start, end, department_id)

    return {
        "headcount": headcount,
        "attrition_pct": attrition_pct,
        "payroll_cost": round(payroll_cost_total, 2),
        "avg_salary": round(float(avg_salary), 2),
        "attendance_rate": attendance["attendance_rate"],
        "headcount_by_department": [
            {"department": department_names.get(dept_id, "Unassigned"), "headcount": count}
            for dept_id, count in sorted(headcount_by_department.items(), key=lambda kv: department_names.get(kv[0], "Unassigned"))
        ],
        "payroll_cost_by_department": [
            {"department": department_names.get(dept_id, "Unassigned"), "cost": round(float(cost), 2)}
            for dept_id, cost in cost_by_department
        ],
        "gender_breakdown": [{"gender": key, "count": value} for key, value in sorted(gender_counts.items())],
        "tenure_breakdown": [{"bucket": key, "count": value} for key, value in tenure_counts.items()],
        "attendance_by_department": attendance["by_department"],
        "trend": attendance["trend"],
        "recent_audit": [
            {
                "id": row.id,
                "action": row.action,
                "entity": row.entity,
                "entity_id": row.entity_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in recent_audit
        ],
        "range": {"start": str(start), "end": str(end)},
    }


def hr_dashboard(db: Session, start: date | None, end: date | None, department_id: int | None):
    start, end = _date_range_defaults(start, end)
    today = business_today(_company_settings(db))

    headcount = len(_active_employees(db, department_id))

    today_query = db.query(Attendance).join(Employee).filter(Attendance.date == today)
    if department_id:
        today_query = today_query.filter(Employee.department_id == department_id)
    today_rows = today_query.all()
    present_today = sum(1 for r in today_rows if r.status in ("present", "late", "half_day", "missing_checkout"))
    late_today = sum(1 for r in today_rows if r.status == "late")

    on_leave_query = (
        db.query(LeaveRequest)
        .join(Employee)
        .filter(LeaveRequest.status == "approved", LeaveRequest.start_date <= today, LeaveRequest.end_date >= today)
    )
    if department_id:
        on_leave_query = on_leave_query.filter(Employee.department_id == department_id)
    on_leave_count = on_leave_query.count()

    pending_leave = db.query(LeaveRequest).filter(LeaveRequest.status == "pending").count()
    pending_corrections = db.query(Attendance).filter(Attendance.correction_status == "pending").count()

    range_query = db.query(Attendance).join(Employee).filter(Attendance.date >= start, Attendance.date <= end)
    if department_id:
        range_query = range_query.filter(Employee.department_id == department_id)
    range_rows = range_query.all()
    present_or_late = sum(1 for r in range_rows if r.status in ("present", "late", "missing_checkout"))
    late_count = sum(1 for r in range_rows if r.status == "late")
    late_pct = round((late_count / present_or_late) * 100, 2) if present_or_late else 0.0

    top_late_query = (
        db.query(Employee.id, Employee.full_name, func.count(Attendance.id).label("late_count"))
        .join(Attendance, Attendance.employee_id == Employee.id)
        .filter(Attendance.status == "late", Attendance.date >= start, Attendance.date <= end)
    )
    if department_id:
        top_late_query = top_late_query.filter(Employee.department_id == department_id)
    top_late = top_late_query.group_by(Employee.id).order_by(func.count(Attendance.id).desc()).limit(5).all()

    attendance = attendance_stats(db, start, end, department_id)

    return {
        "headcount": headcount,
        "present_today": present_today,
        "on_leave_today": on_leave_count,
        "late_today": late_today,
        "pending_leave_approvals": pending_leave,
        "pending_attendance_corrections": pending_corrections,
        "attendance_rate": attendance["attendance_rate"],
        "late_pct": late_pct,
        "absent_count": attendance["absent_days"],
        "top_late_comers": [{"employee_id": eid, "name": name, "late_count": count} for eid, name, count in top_late],
        "leave_by_type": leave_utilization(db, start, end, department_id),
        "attendance_by_department": attendance["by_department"],
        "trend": attendance["trend"],
        "range": {"start": str(start), "end": str(end)},
    }


def employee_dashboard(db: Session, employee: Employee):
    today = business_today(_company_settings(db))
    week_start = today - timedelta(days=today.weekday())
    week_rows = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id, Attendance.date >= week_start, Attendance.date <= today)
        .all()
    )
    hours = 0.0
    for row in week_rows:
        if row.check_in_time and row.check_out_time:
            hours += (row.check_out_time - row.check_in_time).total_seconds() / 3600

    month_rows = (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee.id, Attendance.date >= today.replace(day=1), Attendance.date <= today)
        .all()
    )
    late_count = sum(1 for row in month_rows if row.status == "late")

    last_slip = (
        db.query(Payslip)
        .join(PayrollRun)
        .filter(Payslip.employee_id == employee.id, PayrollRun.status == "finalized")
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
        .first()
    )

    today_row = next((row for row in week_rows if row.date == today), None)

    return {
        "hours_this_week": round(hours, 1),
        "late_count_this_month": late_count,
        "last_payslip_net": last_slip.net_pay if last_slip else None,
        "last_payslip_id": last_slip.id if last_slip else None,
        "today_status": today_row.status if today_row else None,
        "checked_in": bool(today_row and today_row.check_in_time),
        "checked_out": bool(today_row and today_row.check_out_time),
    }
