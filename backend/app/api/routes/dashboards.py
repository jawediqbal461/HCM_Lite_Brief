from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_admin_or_hr, require_any, require_hr
from app.core.clock import business_today
from app.core.database import get_db
from app.models.employee import Employee
from app.services import dashboard_service, insights as insights_service, org_service
from app.services.payroll_service import LATES_PER_PENALTY, PENALTY_DAYS

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


@router.get("/insights")
def insights(
    department_id: int | None = None,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    settings = org_service.get_settings(db)
    today = business_today(settings)
    return {
        "attrition_risk": insights_service.attrition_risk(db, settings, today, department_id),
        "absence_anomalies": insights_service.absence_anomalies(db, settings, today, department_id),
        "late_penalty": {"lates_per_penalty": LATES_PER_PENALTY, "penalty_days": PENALTY_DAYS},
        "as_of": str(today),
    }


@router.get("/me")
def my_dashboard(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    employee = db.get(Employee, current.employee_id)
    return dashboard_service.employee_dashboard(db, employee)
