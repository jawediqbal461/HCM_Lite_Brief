"""Attrition risk and absence anomalies (the brief's bonus insights).

These are explainable heuristics over the records the company already created,
not predictions: every score ships with the factors that produced it so HR can
judge it rather than trust it. Nothing here decides anything on its own.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.org import CompanySettings, Holiday, LeaveType
from app.services.attendance_service import is_weekend

LOOKBACK_DAYS = 90
RECENT_DAYS = 30

HIGH_RISK = 60
MEDIUM_RISK = 35


def _working_days(db: Session, settings: CompanySettings, start: date, end: date) -> list[date]:
    holidays = {h.date for h in db.query(Holiday).filter(Holiday.date >= start, Holiday.date <= end).all()}
    days, day = [], start
    while day <= end:
        if not is_weekend(settings, day) and day not in holidays:
            days.append(day)
        day += timedelta(days=1)
    return days


def _day_statuses(db: Session, settings: CompanySettings, employees: list[Employee], start: date, end: date):
    """{employee_id: {date: status}} across the working days in the window."""
    working_days = _working_days(db, settings, start, end)
    working_set = set(working_days)
    ids = [e.id for e in employees]
    if not ids or not working_days:
        return {}, working_days

    records = {
        (r.employee_id, r.date): r.status
        for r in db.query(Attendance).filter(
            Attendance.employee_id.in_(ids), Attendance.date >= start, Attendance.date <= end
        )
    }

    leave_days: set[tuple[int, date]] = set()
    for leave in db.query(LeaveRequest).filter(
        LeaveRequest.employee_id.in_(ids),
        LeaveRequest.status == "approved",
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start,
    ):
        day = max(leave.start_date, start)
        last = min(leave.end_date, end)
        while day <= last:
            if day in working_set:
                leave_days.add((leave.employee_id, day))
            day += timedelta(days=1)

    statuses: dict[int, dict[date, str]] = {}
    for employee in employees:
        first = max(start, employee.date_of_joining)
        last = min(end, employee.date_of_leaving) if employee.date_of_leaving else end
        per_day = {}
        for day in working_days:
            if day < first or day > last:
                continue
            if (employee.id, day) in leave_days:
                per_day[day] = "on_leave"
            else:
                per_day[day] = records.get((employee.id, day), "absent")
        statuses[employee.id] = per_day
    return statuses, working_days


def _active_employees(db: Session, department_id: int | None) -> list[Employee]:
    query = db.query(Employee).filter(Employee.status.in_(["active", "probation"]))
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    return query.all()


def attrition_risk(db: Session, settings: CompanySettings, today: date, department_id: int | None = None) -> list[dict]:
    employees = _active_employees(db, department_id)
    start = today - timedelta(days=LOOKBACK_DAYS)
    statuses, _ = _day_statuses(db, settings, employees, start, today)

    quotas = {lt.id: lt.annual_quota for lt in db.query(LeaveType).all() if lt.annual_quota}
    total_quota = sum(quotas.values()) or 1

    results = []
    for employee in employees:
        per_day = statuses.get(employee.id, {})
        expected = len([d for d, s in per_day.items() if s != "on_leave"])
        if expected == 0:
            continue

        absent = sum(1 for s in per_day.values() if s == "absent")
        late = sum(1 for s in per_day.values() if s == "late")
        worked = sum(1 for s in per_day.values() if s in ("present", "late", "half_day", "missing_checkout"))

        absence_rate = absent / expected
        late_rate = late / worked if worked else 0.0

        used_leave = sum(
            r.days
            for r in db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date >= date(today.year, 1, 1),
            )
        )
        leave_use = used_leave / total_quota
        tenure_months = (today - employee.date_of_joining).days / 30.44

        score = 0
        factors = []

        if absence_rate >= 0.15:
            score += 30
            factors.append(f"Absent on {absence_rate:.0%} of expected days")
        elif absence_rate >= 0.08:
            score += 15
            factors.append(f"Absence running at {absence_rate:.0%}")

        if late_rate >= 0.30:
            score += 20
            factors.append(f"Late on {late_rate:.0%} of days worked")
        elif late_rate >= 0.15:
            score += 10
            factors.append(f"Late on {late_rate:.0%} of days worked")

        if leave_use >= 0.80:
            score += 15
            factors.append(f"Has used {leave_use:.0%} of the year's leave allowance")

        if tenure_months < 6:
            score += 15
            factors.append("Less than six months in the company")
        elif tenure_months < 12:
            score += 10
            factors.append("Under a year in the company")

        recent_start = today - timedelta(days=RECENT_DAYS)
        recent = [s for d, s in per_day.items() if d >= recent_start]
        earlier = [s for d, s in per_day.items() if d < recent_start]
        recent_absence = (recent.count("absent") / len(recent)) if recent else 0
        earlier_absence = (earlier.count("absent") / len(earlier)) if earlier else 0
        if recent.count("absent") >= 2 and recent_absence >= 2 * max(earlier_absence, 0.01):
            score += 20
            factors.append("Absence has risen sharply in the last month")

        score = min(score, 100)
        if score == 0:
            continue

        results.append(
            {
                "employee_id": employee.id,
                "name": employee.full_name,
                "department": employee.department.name if employee.department else None,
                "score": score,
                "band": "high" if score >= HIGH_RISK else "medium" if score >= MEDIUM_RISK else "low",
                "factors": factors,
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def absence_anomalies(db: Session, settings: CompanySettings, today: date, department_id: int | None = None) -> list[dict]:
    employees = _active_employees(db, department_id)
    start = today - timedelta(days=LOOKBACK_DAYS)
    statuses, _ = _day_statuses(db, settings, employees, start, today)

    results = []
    for employee in employees:
        per_day = statuses.get(employee.id, {})
        if not per_day:
            continue

        absent_days = sorted(d for d, s in per_day.items() if s == "absent")
        late_count = sum(1 for s in per_day.values() if s == "late")
        flags = []

        # Absences that cling to the weekend are the classic pattern HR looks for.
        if len(absent_days) >= 3:
            adjacent = sum(1 for d in absent_days if d.weekday() in (0, 4))
            if adjacent / len(absent_days) >= 0.6:
                flags.append(
                    {
                        "flag": "weekend_adjacent",
                        "label": "Absences cluster on Mondays and Fridays",
                        "detail": f"{adjacent} of {len(absent_days)} absences fell next to a weekend",
                    }
                )

        # Single days scattered around read differently from one honest illness.
        isolated = [
            d
            for d in absent_days
            if (d - timedelta(days=1)) not in per_day or per_day.get(d - timedelta(days=1)) != "absent"
            if (d + timedelta(days=1)) not in per_day or per_day.get(d + timedelta(days=1)) != "absent"
        ]
        if len(isolated) >= 3:
            flags.append(
                {
                    "flag": "repeated_single_days",
                    "label": "Several one-day absences",
                    "detail": f"{len(isolated)} separate single-day absences in the last {LOOKBACK_DAYS} days",
                }
            )

        recent_start = today - timedelta(days=RECENT_DAYS)
        recent_absent = [d for d in absent_days if d >= recent_start]
        earlier_absent = [d for d in absent_days if d < recent_start]
        if len(recent_absent) >= 2 and len(recent_absent) > len(earlier_absent):
            flags.append(
                {
                    "flag": "absence_spike",
                    "label": "Absence rising",
                    "detail": f"{len(recent_absent)} absences in the last {RECENT_DAYS} days vs {len(earlier_absent)} before that",
                }
            )

        if late_count >= 5:
            flags.append(
                {
                    "flag": "frequent_late",
                    "label": "Frequently late",
                    "detail": f"Late {late_count} times in the last {LOOKBACK_DAYS} days",
                }
            )

        if flags:
            results.append(
                {
                    "employee_id": employee.id,
                    "name": employee.full_name,
                    "department": employee.department.name if employee.department else None,
                    "absences": len(absent_days),
                    "lates": late_count,
                    "flags": flags,
                }
            )

    results.sort(key=lambda r: len(r["flags"]), reverse=True)
    return results
