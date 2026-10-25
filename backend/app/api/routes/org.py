from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_admin_or_hr, require_any
from app.core.database import get_db
from app.models.user import User
from app.schemas.org import (
    CompanySettingsIn,
    CompanySettingsOut,
    DepartmentIn,
    DepartmentOut,
    DesignationIn,
    DesignationOut,
    HolidayIn,
    HolidayOut,
    HRUserCreate,
    LeaveTypeIn,
    LeaveTypeOut,
    RoleChange,
    UserOut,
)
from app.services import auth_service, org_service

router = APIRouter(prefix="/org", tags=["organization"])


@router.get("/settings", response_model=CompanySettingsOut)
def get_settings(current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    return org_service.get_settings(db)


@router.put("/settings", response_model=CompanySettingsOut)
def update_settings(payload: CompanySettingsIn, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return org_service.update_settings(db, current.id, payload.model_dump(exclude_none=True))


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    from app.models.org import Department

    return db.query(Department).order_by(Department.name).all()


@router.post("/departments", response_model=DepartmentOut)
def create_department(payload: DepartmentIn, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return org_service.create_department(db, current.id, payload.name)


@router.get("/designations", response_model=list[DesignationOut])
def list_designations(current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    from app.models.org import Designation

    return db.query(Designation).order_by(Designation.name).all()


@router.post("/designations", response_model=DesignationOut)
def create_designation(payload: DesignationIn, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return org_service.create_designation(db, current.id, payload.name)


@router.get("/leave-types", response_model=list[LeaveTypeOut])
def list_leave_types(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    from app.models.org import LeaveType

    return db.query(LeaveType).order_by(LeaveType.name).all()


@router.post("/leave-types", response_model=LeaveTypeOut)
def create_leave_type(payload: LeaveTypeIn, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return org_service.create_leave_type(db, current.id, payload.name, payload.annual_quota)


@router.get("/holidays", response_model=list[HolidayOut])
def list_holidays(current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    from app.models.org import Holiday

    return db.query(Holiday).order_by(Holiday.date).all()


@router.post("/holidays", response_model=HolidayOut)
def create_holiday(payload: HolidayIn, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return org_service.create_holiday(db, current.id, payload.date, payload.name)


@router.post("/hr-users")
def create_hr_user(payload: HRUserCreate, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    user = auth_service.create_hr_user(
        db,
        current.id,
        payload.full_name,
        payload.email,
        payload.password,
        require_password_change=payload.require_password_change,
    )
    return {"id": user.id, "email": user.email, "must_change_password": user.must_change_password}


@router.get("/users", response_model=list[UserOut])
def list_users(current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.role, User.email).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_user_role(user_id: int, payload: RoleChange, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return auth_service.change_user_role(db, current.id, user, payload.role)


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: int, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    auth_service.set_user_active(db, current.id, user, False)
    return {"ok": True}


@router.post("/users/{user_id}/reactivate")
def reactivate_user(user_id: int, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    auth_service.set_user_active(db, current.id, user, True)
    return {"ok": True}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    temp_password = auth_service.reset_user_password(db, current.id, user)
    return {"temporary_password": temp_password}
