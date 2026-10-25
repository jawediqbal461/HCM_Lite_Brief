from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.clock import business_now, business_today
from app.services.geofence import check_camera_attendance
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.org import CompanySettings, Holiday
from app.services.audit_service import log_action, notify


def is_weekend(settings: CompanySettings, d: date) -> bool:
    weekend_days = {int(x) for x in settings.weekend_days.split(",") if x.strip() != ""}
    return d.weekday() in weekend_days


def is_holiday(db: Session, d: date) -> bool:
    return db.query(Holiday).filter(Holiday.date == d).first() is not None


def has_approved_leave(db: Session, employee_id: int, d: date) -> bool:
    return (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= d,
            LeaveRequest.end_date >= d,
        )
        .first()
        is not None
    )


def check_in(
    db: Session,
    settings: CompanySettings,
    employee: Employee,
    source: str = "web",
    camera: dict | None = None,
) -> Attendance:
    if source == "camera":
        result = check_camera_attendance(
            settings,
            face_detected=(camera or {}).get("face_detected"),
            faces_count=(camera or {}).get("faces_count"),
            lat=(camera or {}).get("lat"),
            lng=(camera or {}).get("lng"),
            accuracy=(camera or {}).get("accuracy"),
        )
        if not result.ok:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, result.reason)

    now = business_now(settings)
    today = now.date()

    existing = db.query(Attendance).filter(Attendance.employee_id == employee.id, Attendance.date == today).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already checked in today")

    if is_weekend(settings, today) or is_holiday(db, today):
        status_value = "present"  # working on a day off is allowed, counted present
    else:
        local_time = now.time()
        grace_cutoff = (datetime.combine(today, settings.office_start_time) + timedelta(minutes=settings.grace_minutes)).time()
        status_value = "late" if local_time > grace_cutoff else "present"

    record = Attendance(employee_id=employee.id, date=today, check_in_time=now, status=status_value, source=source)
    db.add(record)
    db.flush()
    log_action(db, None, "create", "attendance", record.id, after={"employee_id": employee.id, "status": status_value})
    db.commit()
    db.refresh(record)
    return record


def check_out(db: Session, settings: CompanySettings, employee: Employee) -> Attendance:
    today = business_today(settings)
    record = db.query(Attendance).filter(Attendance.employee_id == employee.id, Attendance.date == today).first()
    if record is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No check-in found for today")
    if record.check_out_time is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already checked out today")

    now = business_now(settings)
    record.check_out_time = now

    check_in = record.check_in_time
    if check_in.tzinfo is None:
        check_in = check_in.replace(tzinfo=now.tzinfo)
    hours_worked = (now - check_in).total_seconds() / 3600
    if hours_worked < settings.half_day_hours:
        record.status = "half_day"

    db.flush()
    log_action(db, None, "update", "attendance", record.id, after={"check_out_time": str(now), "status": record.status})
    db.commit()
    db.refresh(record)
    return record


def finalize_missing_checkouts(db: Session, before_date: date):
    """Mark yesterday-and-earlier open check-ins as missing_checkout. Call lazily from dashboards/payroll.

    Only rows with an actual check-in qualify: an absent day raised for correction also has
    no check-out time, and must not be rewritten into a missing_checkout.
    """
    rows = (
        db.query(Attendance)
        .filter(
            Attendance.date < before_date,
            Attendance.check_in_time.is_not(None),
            Attendance.check_out_time.is_(None),
            Attendance.status.notin_(["missing_checkout"]),
        )
        .all()
    )
    for r in rows:
        r.status = "missing_checkout"
    if rows:
        db.commit()


def request_correction(db: Session, employee: Employee, d: date, reason: str) -> Attendance:
    record = db.query(Attendance).filter(Attendance.employee_id == employee.id, Attendance.date == d).first()
    if record is None:
        record = Attendance(employee_id=employee.id, date=d, status="absent", source="web")
        db.add(record)
        db.flush()
    record.correction_requested = True
    record.correction_reason = reason
    record.correction_status = "pending"
    db.commit()
    db.refresh(record)
    return record


def decide_correction(db: Session, actor_id: int, record: Attendance, approve: bool, comment: str | None):
    record.correction_status = "approved" if approve else "rejected"
    if approve:
        record.status = "present"
    db.flush()
    log_action(db, actor_id, "approve" if approve else "reject", "attendance_correction", record.id, after={"approve": approve, "comment": comment})
    if record.employee.user:
        notify(db, record.employee.user.id, f"Your attendance correction for {record.date} was {'approved' if approve else 'rejected'}.")
    db.commit()
    db.refresh(record)
    return record


def daily_board(db: Session, settings: CompanySettings, d: date) -> list[dict]:
    """One row per employee who was employed on that day, including absent and on-leave staff.

    Attendance rows only exist for people who checked in, so everyone else has to be
    derived: approved leave first, then the weekend/holiday calendar, then absent.
    """
    employees = (
        db.query(Employee)
        .filter(Employee.status.in_(["active", "probation"]), Employee.date_of_joining <= d)
        .order_by(Employee.full_name)
        .all()
    )
    records = {r.employee_id: r for r in db.query(Attendance).filter(Attendance.date == d).all()}
    non_working = is_weekend(settings, d) or is_holiday(db, d)

    rows = []
    for employee in employees:
        if employee.date_of_leaving and employee.date_of_leaving < d:
            continue

        record = records.get(employee.id)
        if record is not None:
            status = record.status
        elif has_approved_leave(db, employee.id, d):
            status = "on_leave"
        elif non_working:
            status = "holiday" if is_holiday(db, d) else "weekend"
        else:
            status = "absent"

        rows.append(
            {
                "employee_id": employee.id,
                "employee_name": employee.full_name,
                "employee_code": employee.code,
                "department": employee.department.name if employee.department else None,
                "date": d,
                "check_in_time": record.check_in_time if record else None,
                "check_out_time": record.check_out_time if record else None,
                "status": status,
                "source": record.source if record else None,
                "attendance_id": record.id if record else None,
                "correction_status": record.correction_status if record else None,
            }
        )
    return rows


def employee_calendar(db: Session, employee_id: int, start: date, end: date):
    return (
        db.query(Attendance)
        .filter(Attendance.employee_id == employee_id, Attendance.date >= start, Attendance.date <= end)
        .order_by(Attendance.date)
        .all()
    )
