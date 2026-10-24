from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, id: int, email: str, role: str, employee_id: int | None):
        self.id = id
        self.email = email
        self.role = role
        self.employee_id = employee_id


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(creds.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return CurrentUser(id=user.id, email=user.email, role=user.role, employee_id=user.employee_id)


def require_roles(*roles: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for your role")
        return user

    return dependency


require_admin = require_roles("admin")
require_hr = require_roles("hr")
require_admin_or_hr = require_roles("admin", "hr")
require_any = require_roles("admin", "hr", "employee")
