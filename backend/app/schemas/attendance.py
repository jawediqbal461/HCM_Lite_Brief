from datetime import date, datetime

from pydantic import BaseModel


class CheckInRequest(BaseModel):
    source: str = "web"  # web | camera
    # Only meaningful when source == "camera"; the server re-checks all of it.
    lat: float | None = None
    lng: float | None = None
    accuracy: float | None = None
    face_detected: bool | None = None
    faces_count: int | None = None


class CheckOutRequest(BaseModel):
    pass


class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    employee_code: str | None = None
    date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: str
    source: str
    correction_requested: bool
    correction_reason: str | None
    correction_status: str

    class Config:
        from_attributes = True


class AttendanceBoardRow(BaseModel):
    """One row per active employee for a given day, including those who never checked in."""

    employee_id: int
    employee_name: str
    employee_code: str
    department: str | None = None
    date: date
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    # present | late | half_day | missing_checkout | on_leave | absent | weekend | holiday
    status: str
    source: str | None = None
    attendance_id: int | None = None
    correction_status: str | None = None


class CorrectionRequest(BaseModel):
    date: date
    reason: str


class CorrectionDecision(BaseModel):
    approve: bool
    comment: str | None = None
