from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin_or_hr, require_any, require_hr
from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeCreatedOut, EmployeeOut, EmployeeSelfUpdate, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


def _get_employee_or_404(db: Session, employee_id: int) -> Employee:
    emp = db.get(Employee, employee_id)
    if emp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return emp


@router.post("", response_model=EmployeeCreatedOut)
def register_employee(payload: EmployeeCreate, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    employee, temp_password = employee_service.register_employee(db, current.id, payload.model_dump())
    return EmployeeCreatedOut(employee=employee, temporary_password=temp_password)


@router.get("", response_model=dict)
def list_employees(
    search: str | None = None,
    department_id: int | None = None,
    status_: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current: CurrentUser = Depends(require_admin_or_hr),
    db: Session = Depends(get_db),
):
    items, total = employee_service.list_employees(db, search, department_id, status_, page, page_size)
    return {"items": [EmployeeOut.model_validate(e) for e in items], "total": total, "page": page, "page_size": page_size}


@router.get("/me", response_model=EmployeeOut)
def my_profile(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    return _get_employee_or_404(db, current.employee_id)


@router.patch("/me", response_model=EmployeeOut)
def update_my_profile(payload: EmployeeSelfUpdate, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    if not current.employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee profile for this account")
    emp = _get_employee_or_404(db, current.employee_id)
    return employee_service.update_employee(db, current.id, emp, payload.model_dump())


@router.get("/export-csv", response_class=PlainTextResponse)
def export_csv(current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    return employee_service.export_csv(db)


@router.post("/import-csv/dry-run")
async def import_csv_dry_run(file: UploadFile, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    content = await file.read()
    return {"rows": employee_service.csv_dry_run(db, content)}


@router.post("/import-csv")
async def import_csv(file: UploadFile, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    content = await file.read()
    return employee_service.csv_import(db, current.id, content)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    if current.role == "employee" and current.employee_id != employee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own profile")
    return _get_employee_or_404(db, employee_id)


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, payload: EmployeeUpdate, current: CurrentUser = Depends(require_hr), db: Session = Depends(get_db)):
    emp = _get_employee_or_404(db, employee_id)
    return employee_service.update_employee(db, current.id, emp, payload.model_dump())
