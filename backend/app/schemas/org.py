from datetime import date, time

from pydantic import BaseModel


class DepartmentIn(BaseModel):
    name: str


class DepartmentOut(DepartmentIn):
    id: int

    class Config:
        from_attributes = True


class DesignationIn(BaseModel):
    name: str


class DesignationOut(DesignationIn):
    id: int

    class Config:
        from_attributes = True


class LeaveTypeIn(BaseModel):
    name: str
    annual_quota: int | None = None


class LeaveTypeOut(LeaveTypeIn):
    id: int

    class Config:
        from_attributes = True


class HolidayIn(BaseModel):
    date: date
    name: str


class HolidayOut(HolidayIn):
    id: int

    class Config:
        from_attributes = True


class CompanySettingsIn(BaseModel):
    company_name: str | None = None
    timezone: str | None = None
    office_start_time: time | None = None
    grace_minutes: int | None = None
    half_day_hours: float | None = None
    weekend_days: str | None = None
    office_lat: float | None = None
    office_lng: float | None = None
    office_radius_m: int | None = None


class CompanySettingsOut(BaseModel):
    id: int
    company_name: str
    timezone: str
    office_start_time: time
    grace_minutes: int
    half_day_hours: float
    weekend_days: str
    office_lat: float | None
    office_lng: float | None
    office_radius_m: int

    class Config:
        from_attributes = True


class HRUserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    # Off for a shared demo login that several people need to sign in with.
    require_password_change: bool = True


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    must_change_password: bool
    employee_id: int | None = None
    employee_name: str | None = None
    employee_code: str | None = None

    class Config:
        from_attributes = True


class RoleChange(BaseModel):
    role: str
