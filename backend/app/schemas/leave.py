from datetime import date, datetime

from pydantic import BaseModel


class LeaveApply(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: str


class LeaveDecision(BaseModel):
    approve: bool
    comment: str | None = None


class LeaveOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    leave_type_id: int
    leave_type_name: str | None = None
    start_date: date
    end_date: date
    days: float
    reason: str
    status: str
    approver_comment: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class LeaveBalanceOut(BaseModel):
    leave_type_id: int
    leave_type_name: str
    quota: int | None
    used: float
    remaining: float | None


class SmartLeaveRequest(BaseModel):
    text: str


class SmartLeaveSuggestion(BaseModel):
    leave_type_id: int | None
    leave_type_name: str | None
    start_date: date | None
    end_date: date | None
    reason: str | None
    raw_text: str
