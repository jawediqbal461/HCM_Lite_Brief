from datetime import date

from pydantic import BaseModel, EmailStr


class EmployeeCreate(BaseModel):
    code: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    gender: str | None = None
    department_id: int | None = None
    designation_id: int | None = None
    date_of_joining: date
    basic_salary: float = 0


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    department_id: int | None = None
    designation_id: int | None = None
    status: str | None = None
    basic_salary: float | None = None
    date_of_leaving: date | None = None


class EmployeeSelfUpdate(BaseModel):
    phone: str | None = None
    address: str | None = None


class EmployeeOut(BaseModel):
    id: int
    code: str
    full_name: str
    email: str
    phone: str | None
    address: str | None
    gender: str | None
    department_id: int | None
    designation_id: int | None
    date_of_joining: date
    date_of_leaving: date | None
    status: str
    basic_salary: float

    class Config:
        from_attributes = True


class EmployeeCreatedOut(BaseModel):
    employee: EmployeeOut
    temporary_password: str


class CSVImportRow(BaseModel):
    row: int
    field: str | None = None
    reason: str | None = None
    ok: bool
