from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin_or_hr, require_any, require_hr
from app.core.database import get_db
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.schemas.leave import LeaveApply, LeaveBalanceOut, LeaveDecision, LeaveOut, SmartLeaveRequest, SmartLeaveSuggestion
from app.services import ai_service, leave_service, org_service

router = APIRouter(prefix="/leave", tags=["leave"])


def _employee_for(current: CurrentUser, db: Session) -> Employee:
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    return db.get(Employee, current.employee_id)


@router.post("/apply", response_model=LeaveOut)
def apply(payload: LeaveApply, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    settings = org_service.get_settings(db)
    return leave_service.apply_leave(db, settings, employee, payload.leave_type_id, payload.start_date, payload.end_date, payload.reason)


@router.post("/{leave_id}/cancel", response_model=LeaveOut)
def cancel(leave_id: int, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    req = db.get(LeaveRequest, leave_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave request not found")
    return leave_service.cancel_leave(db, employee, req)


@router.get("/mine", response_model=list[LeaveOut])
def my_leaves(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    return db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee.id).order_by(LeaveRequest.created_at.desc()).all()


@router.get("/balance", response_model=list[LeaveBalanceOut])
def balance(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    return leave_service.leave_balance(db, employee.id, date.today().year)


@router.get("", response_model=list[LeaveOut])
def all_leave(
    status_filter: str | None = Query(None, alias="status"),
    employee_id: int | None = None,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    query = db.query(LeaveRequest)
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.get("/inbox", response_model=list[LeaveOut])
def inbox(current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    return db.query(LeaveRequest).filter(LeaveRequest.status == "pending").order_by(LeaveRequest.created_at).all()


@router.post("/{leave_id}/decide", response_model=LeaveOut)
def decide(leave_id: int, payload: LeaveDecision, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    req = db.get(LeaveRequest, leave_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave request not found")
    return leave_service.decide_leave(db, current.id, req, payload.approve, payload.comment)


@router.post("/smart", response_model=SmartLeaveSuggestion)
def smart_leave(payload: SmartLeaveRequest, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    result = ai_service.smart_leave(db, current, payload.text)
    return SmartLeaveSuggestion(**result)
