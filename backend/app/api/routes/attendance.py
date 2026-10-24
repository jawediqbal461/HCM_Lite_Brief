from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin_or_hr, require_any, require_hr
from app.core.database import get_db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.core.clock import business_today
from app.schemas.attendance import (
    AttendanceBoardRow,
    AttendanceOut,
    CheckInRequest,
    CorrectionDecision,
    CorrectionRequest,
)
from app.services import attendance_service, org_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _employee_for(current: CurrentUser, db: Session) -> Employee:
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    return db.get(Employee, current.employee_id)


@router.post("/check-in", response_model=AttendanceOut)
def check_in(payload: CheckInRequest, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    settings = org_service.get_settings(db)
    return attendance_service.check_in(db, settings, employee, source=payload.source)


@router.post("/check-out", response_model=AttendanceOut)
def check_out(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    settings = org_service.get_settings(db)
    return attendance_service.check_out(db, settings, employee)


@router.get("/board", response_model=list[AttendanceBoardRow])
def board(day: date | None = None, current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    settings = org_service.get_settings(db)
    today = business_today(settings)
    attendance_service.finalize_missing_checkouts(db, today)
    return attendance_service.daily_board(db, settings, day or today)


@router.get("/calendar", response_model=list[AttendanceOut])
def calendar(
    start: date,
    end: date,
    employee_id: int | None = None,
    current: CurrentUser = Depends(require_any),
    db: Session = Depends(get_db),
):
    if current.role == "employee":
        employee_id = current.employee_id
    elif employee_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "employee_id is required")
    return attendance_service.employee_calendar(db, employee_id, start, end)


@router.post("/corrections", response_model=AttendanceOut)
def request_correction(payload: CorrectionRequest, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    return attendance_service.request_correction(db, employee, payload.date, payload.reason)


@router.get("/corrections/pending", response_model=list[AttendanceOut])
def pending_corrections(current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    return db.query(Attendance).filter(Attendance.correction_status == "pending").all()


@router.post("/corrections/{attendance_id}/decide", response_model=AttendanceOut)
def decide_correction(attendance_id: int, payload: CorrectionDecision, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    record = db.get(Attendance, attendance_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attendance record not found")
    return attendance_service.decide_correction(db, current.id, record, payload.approve, payload.comment)
