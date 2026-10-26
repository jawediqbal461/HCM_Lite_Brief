from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin_or_hr, require_any, require_hr
from app.core.database import get_db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.org import Department
from app.services import export_service
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
    return attendance_service.check_in(
        db,
        settings,
        employee,
        source=payload.source,
        camera={
            "face_detected": payload.face_detected,
            "faces_count": payload.faces_count,
            "lat": payload.lat,
            "lng": payload.lng,
            "accuracy": payload.accuracy,
        },
    )


@router.post("/check-out", response_model=AttendanceOut)
def check_out(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    employee = _employee_for(current, db)
    settings = org_service.get_settings(db)
    return attendance_service.check_out(db, settings, employee)


def _board_rows(db: Session, day: date | None, department_id: int | None, status_filter: str | None, search: str | None):
    settings = org_service.get_settings(db)
    today = business_today(settings)
    attendance_service.finalize_missing_checkouts(db, today)
    rows = attendance_service.daily_board(db, settings, day or today)

    if department_id:
        names = {d.id: d.name for d in db.query(Department).all()}
        wanted = names.get(department_id)
        rows = [r for r in rows if r["department"] == wanted]
    if status_filter:
        rows = [r for r in rows if r["status"] == status_filter]
    if search:
        needle = search.lower()
        rows = [r for r in rows if needle in r["employee_name"].lower() or needle in r["employee_code"].lower()]
    return rows


@router.get("/board", response_model=list[AttendanceBoardRow])
def board(
    day: date | None = None,
    department_id: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    return _board_rows(db, day, department_id, status_filter, search)


@router.get("/board/export-csv", response_class=PlainTextResponse)
def board_csv(
    day: date | None = None,
    department_id: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    return export_service.attendance_csv(_board_rows(db, day, department_id, status_filter, search))


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
