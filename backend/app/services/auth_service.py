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


def create_hr_user(
    db: Session,
    actor_id: int,
    full_name: str,
    email: str,
    password: str,
    require_password_change: bool = True,
) -> User:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already in use")
    user = User(
        email=email,
        password_hash=hash_password(password),
        role="hr",
        must_change_password=require_password_change,
    )
    db.add(user)
    db.flush()
    log_action(db, actor_id, "create", "user", user.id, after={"email": email, "role": "hr", "full_name": full_name})
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, actor_id: int, user: User, active: bool):
    if not active:
        if user.id == actor_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own login")
        if user.role == "admin" and _active_admin_count(db, excluding_user_id=user.id) == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This is the last active Admin and cannot be deactivated")

    before = {"is_active": user.is_active}
    user.is_active = active
    db.flush()
    log_action(db, actor_id, "update", "user", user.id, before=before, after={"is_active": active})
    db.commit()


VALID_ROLES = ("admin", "hr", "employee")


def _active_admin_count(db: Session, excluding_user_id: int | None = None) -> int:
    query = db.query(User).filter(User.role == "admin", User.is_active.is_(True))
    if excluding_user_id is not None:
        query = query.filter(User.id != excluding_user_id)
    return query.count()


def change_user_role(db: Session, actor_id: int, user: User, new_role: str) -> User:
    if new_role not in VALID_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role must be one of {', '.join(VALID_ROLES)}")
    if user.id == actor_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")
    if user.role == new_role:
        return user

    # An "employee" reads rows by employee_id, so a login with no employee record
    # would land in a broken state where most of its own pages fail.
    if new_role == "employee" and user.employee_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This login is not linked to an employee record, so it cannot become an Employee.",
        )
    if user.role == "admin" and _active_admin_count(db, excluding_user_id=user.id) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This is the last active Admin; promote someone else first")

    before = {"role": user.role}
    user.role = new_role
    db.flush()
    log_action(db, actor_id, "update", "user", user.id, before=before, after={"role": new_role})
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, actor_id: int, user: User) -> str:
    temp_password = generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True
    db.flush()
    log_action(db, actor_id, "update", "user", user.id, after={"action": "password_reset"})
    db.commit()
    return temp_password
