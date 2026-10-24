from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # present | late | half_day | absent | missing_checkout | on_leave
    status: Mapped[str] = mapped_column(String(20), default="present")
    source: Mapped[str] = mapped_column(String(10), default="web")  # web | camera

    correction_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # none | pending | approved | rejected
    correction_status: Mapped[str] = mapped_column(String(20), default="none")

    employee: Mapped["Employee"] = relationship()

    @property
    def employee_name(self) -> str | None:
        return self.employee.full_name if self.employee else None

    @property
    def employee_code(self) -> str | None:
        return self.employee.code if self.employee else None
