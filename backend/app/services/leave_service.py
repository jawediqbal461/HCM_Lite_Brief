from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.org import CompanySettings, Holiday, LeaveType
from app.services.attendance_service import is_weekend
from app.services.audit_service import log_action, notify


def working_days_between(db: Session, settings: CompanySettings, start: date, end: date) -> float:
    holidays = {h.date for h in db.query(Holiday).filter(Holiday.date >= start, Holiday.date <= end).all()}
    count = 0
    d = start
    while d <= end:
        if not is_weekend(settings, d) and d not in holidays:
            count += 1
        d += timedelta(days=1)
    return float(count)


def used_days(db: Session, employee_id: int, leave_type_id: int, year: int) -> float:
    rows = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type_id,
            LeaveRequest.status == "approved",
        )
        .all()
    )
    return sum(r.days for r in rows if r.start_date.year == year)


def apply_leave(db: Session, settings: CompanySettings, employee: Employee, leave_type_id: int, start: date, end: date, reason: str) -> LeaveRequest:
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "end_date must be on or after start_date")

    leave_type = db.get(LeaveType, leave_type_id)
    if leave_type is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown leave type")

    overlap = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start,
        )
        .first()
    )
    if overlap is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Overlaps with an existing leave request")

    days = working_days_between(db, settings, start, end)
    if days <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Selected range has no working days")

    if leave_type.annual_quota is not None:
        already_used = used_days(db, employee.id, leave_type_id, start.year)
        if already_used + days > leave_type.annual_quota:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Requested days exceed remaining leave balance")

    request = LeaveRequest(employee_id=employee.id, leave_type_id=leave_type_id, start_date=start, end_date=end, days=days, reason=reason)
    db.add(request)
    db.flush()
    log_action(db, employee.user.id if employee.user else None, "create", "leave_request", request.id, after={"start": str(start), "end": str(end), "days": days})
    db.commit()
    db.refresh(request)
    return request


def cancel_leave(db: Session, employee: Employee, request: LeaveRequest) -> LeaveRequest:
    if request.employee_id != employee.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your leave request")
    if request.status not in ("pending", "approved"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot cancel this request")
    request.status = "cancelled"
    db.commit()
    db.refresh(request)
    return request


def decide_leave(db: Session, actor_id: int, request: LeaveRequest, approve: bool, comment: str | None) -> LeaveRequest:
    if request.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request already decided")
    request.status = "approved" if approve else "rejected"
    request.approver_comment = comment
    request.approved_by = actor_id
    db.flush()
    log_action(db, actor_id, "approve" if approve else "reject", "leave_request", request.id, after={"comment": comment})
    if request.employee.user:
        notify(db, request.employee.user.id, f"Your leave request ({request.start_date} to {request.end_date}) was {request.status}.")
    db.commit()
    db.refresh(request)
    return request


def leave_balance(db: Session, employee_id: int, year: int):
    leave_types = db.query(LeaveType).all()
    result = []
    for lt in leave_types:
        used = used_days(db, employee_id, lt.id, year)
        remaining = None if lt.annual_quota is None else lt.annual_quota - used
        result.append(
            {
                "leave_type_id": lt.id,
                "leave_type_name": lt.name,
                "quota": lt.annual_quota,
                "used": used,
                "remaining": remaining,
            }
        )
    return result
