from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_any, require_hr
from app.core.database import get_db
from app.models.employee import Employee
from app.services import dashboard_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/admin")
def admin_dashboard(
    start: date | None = None,
    end: date | None = None,
    department_id: int | None = None,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return dashboard_service.admin_dashboard(db, start, end, department_id)


@router.get("/hr")
def hr_dashboard(
    start: date | None = None,
    end: date | None = None,
    department_id: int | None = None,
    current: CurrentUser = Depends(require_hr),
    db: Session = Depends(get_db),
):
    return dashboard_service.hr_dashboard(db, start, end, department_id)


@router.get("/me")
def my_dashboard(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    employee = db.get(Employee, current.employee_id)
    return dashboard_service.employee_dashboard(db, employee)
