from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_any
from app.core.clock import business_today
from app.core.database import get_db
from app.models.employee import Employee
from app.services import org_service, reports

router = APIRouter(prefix="/reports", tags=["reports"])


def _build(
    db: Session,
    current: CurrentUser,
    key: str,
    start: date | None,
    end: date | None,
    month: int | None,
    year: int | None,
    department_id: int | None,
) -> dict:
    settings = org_service.get_settings(db)
    today = business_today(settings)

    spec = reports.REPORTS.get(key)
    if spec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown report")

    params: dict = {}
    wanted = spec["params"]
    if "range" in wanted:
        params["end"] = end or today
        params["start"] = start or (params["end"] - timedelta(days=30))
    if "month" in wanted:
        params["month"] = month or today.month
        params["year"] = year or today.year
    if "year" in wanted and "month" not in wanted:
        params["year"] = year or today.year
    if "department" in wanted:
        params["department_id"] = department_id

    employee = db.get(Employee, current.employee_id) if current.employee_id else None
    return reports.run(db, settings, key, current.role, employee, params)


@router.get("")
def list_reports(current: CurrentUser = Depends(require_any)):
    return {"reports": reports.available(current.role)}


@router.get("/{key}")
def run_report(
    key: str,
    start: date | None = None,
    end: date | None = None,
    month: int | None = None,
    year: int | None = None,
    department_id: int | None = None,
    current: CurrentUser = Depends(require_any),
    db: Session = Depends(get_db),
):
    return _build(db, current, key, start, end, month, year, department_id)


@router.get("/{key}/export-csv", response_class=PlainTextResponse)
def export_report(
    key: str,
    start: date | None = None,
    end: date | None = None,
    month: int | None = None,
    year: int | None = None,
    department_id: int | None = None,
    current: CurrentUser = Depends(require_any),
    db: Session = Depends(get_db),
):
    return reports.to_csv(_build(db, current, key, start, end, month, year, department_id))
