from pydantic import BaseModel, EmailStr


class FirstRunSetup(BaseModel):
    company_name: str
    admin_email: EmailStr
    admin_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    must_change_password: bool
    employee_id: int | None = None
    full_name: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class MeResponse(BaseModel):
    id: int
    email: str
    role: str
    employee_id: int | None = None
    full_name: str | None = None
