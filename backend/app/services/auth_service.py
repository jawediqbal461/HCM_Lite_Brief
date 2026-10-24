import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.org import CompanySettings
from app.models.user import User
from app.services.audit_service import log_action


def is_first_run(db: Session) -> bool:
    return db.query(CompanySettings).first() is None


def first_run_setup(db: Session, company_name: str, admin_email: str, admin_password: str) -> User:
    if not is_first_run(db):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Company is already set up")

    settings_row = CompanySettings(company_name=company_name)
    db.add(settings_row)

    admin = User(
        email=admin_email,
        password_hash=hash_password(admin_password),
        role="admin",
        employee_id=None,
        must_change_password=False,
    )
    db.add(admin)
    db.flush()
    log_action(db, admin.id, "create", "company_settings", settings_row.id, after={"company_name": company_name})
    db.commit()
    db.refresh(admin)
    return admin


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return user


def issue_token(user: User) -> str:
    return create_access_token(subject=str(user.id), role=user.role, employee_id=user.employee_id)


def change_password(db: Session, user: User, old_password: str, new_password: str):
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Old password is incorrect")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()


def generate_temp_password() -> str:
    return secrets.token_urlsafe(9)


def create_hr_user(db: Session, actor_id: int, full_name: str, email: str, password: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already in use")
    user = User(email=email, password_hash=hash_password(password), role="hr", must_change_password=True)
    db.add(user)
    db.flush()
    log_action(db, actor_id, "create", "user", user.id, after={"email": email, "role": "hr", "full_name": full_name})
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, actor_id: int, user: User, active: bool):
    before = {"is_active": user.is_active}
    user.is_active = active
    db.flush()
    log_action(db, actor_id, "update", "user", user.id, before=before, after={"is_active": active})
    db.commit()


def reset_user_password(db: Session, actor_id: int, user: User) -> str:
    temp_password = generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True
    db.flush()
    log_action(db, actor_id, "update", "user", user.id, after={"action": "password_reset"})
    db.commit()
    return temp_password
