from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, FirstRunSetup, LoginRequest, MeResponse, TokenResponse
from app.services import auth_service, org_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/first-run-status")
def first_run_status(db: Session = Depends(get_db)):
    return {"first_run": auth_service.is_first_run(db)}


@router.post("/first-run-setup", response_model=TokenResponse)
def first_run_setup(payload: FirstRunSetup, db: Session = Depends(get_db)):
    admin = auth_service.first_run_setup(db, payload.company_name, payload.admin_email, payload.admin_password)
    org_service.seed_default_leave_types(db, admin.id)
    token = auth_service.issue_token(admin)
    return TokenResponse(access_token=token, role=admin.role, must_change_password=admin.must_change_password, full_name=payload.company_name)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    token = auth_service.issue_token(user)
    full_name = user.employee.full_name if user.employee else user.email
    return TokenResponse(
        access_token=token,
        role=user.role,
        must_change_password=user.must_change_password,
        employee_id=user.employee_id,
        full_name=full_name,
    )


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, current.id)
    auth_service.change_password(db, user, payload.old_password, payload.new_password)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, current.id)
    full_name = user.employee.full_name if user.employee else None
    return MeResponse(id=user.id, email=user.email, role=user.role, employee_id=user.employee_id, full_name=full_name)
