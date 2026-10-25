from datetime import datetime

from pydantic import BaseModel


class PayrollRunCreate(BaseModel):
    month: int
    year: int


class PayslipOut(BaseModel):
    id: int
    payroll_run_id: int
    employee_id: int
    employee_name: str | None = None
    employee_code: str | None = None
    basic: float
    hra: float
    medical: float
    gross: float
    working_days: int
    present_days: float
    absent_days: float
    unpaid_days: float
    half_days: float
    late_penalty_days: float = 0
    deductions: float
    tax: float
    net_pay: float

    class Config:
        from_attributes = True


class PayrollRunOut(BaseModel):
    id: int
    month: int
    year: int
    status: str
    created_at: datetime
    finalized_at: datetime | None
    payslips: list[PayslipOut] = []

    class Config:
        from_attributes = True
