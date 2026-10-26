from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin_or_hr, require_any, require_hr
from app.schemas.common import Page, paginate
from app.core.database import get_db
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.schemas.leave import LeaveApply, LeaveBalanceOut, LeaveDecision, LeaveOut, SmartLeaveRequest, SmartLeaveSuggestion
from app.services import ai_service, export_service, leave_service, org_service

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
def my_leaves(
    year: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    leave_type_id: int | None = None,
    current: CurrentUser = Depends(require_any),
    db: Session = Depends(get_db),
):
    employee = _employee_for(current, db)
    query = db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee.id)
    if year:
        query = query.filter(LeaveRequest.start_date >= date(year, 1, 1), LeaveRequest.start_date <= date(year, 12, 31))
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if leave_type_id:
        query = query.filter(LeaveRequest.leave_type_id == leave_type_id)
    return query.order_by(LeaveRequest.created_at.desc()).all()


@router.get("/balance", response_model=list[LeaveBalanceOut])
def balance(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    return leave_service.leave_balance(db, employee.id, date.today().year)


@router.get("", response_model=Page[LeaveOut])
def all_leave(
    status_filter: str | None = Query(None, alias="status"),
    employee_id: int | None = None,
    leave_type_id: int | None = None,
    department_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    query = db.query(LeaveRequest).join(Employee, LeaveRequest.employee_id == Employee.id)
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    if leave_type_id:
        query = query.filter(LeaveRequest.leave_type_id == leave_type_id)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    # Overlap, not containment: a leave spanning the range edge still belongs in it.
    if start:
        query = query.filter(LeaveRequest.end_date >= start)
    if end:
        query = query.filter(LeaveRequest.start_date <= end)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Employee.full_name.ilike(like), Employee.code.ilike(like)))

    items, total, page, page_size = paginate(query.order_by(LeaveRequest.created_at.desc()), page, page_size)
    return Page[LeaveOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/export-csv", response_class=PlainTextResponse)
def export_leave_csv(
    status_filter: str | None = Query(None, alias="status"),
    department_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    query = db.query(LeaveRequest).join(Employee, LeaveRequest.employee_id == Employee.id)
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if start:
        query = query.filter(LeaveRequest.end_date >= start)
    if end:
        query = query.filter(LeaveRequest.start_date <= end)
    return export_service.leave_csv(query.order_by(LeaveRequest.start_date.desc()).all())


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
