from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"))

    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(300))

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected|cancelled
    approver_comment: Mapped[str | None] = mapped_column(String(300), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped["Employee"] = relationship()
    leave_type: Mapped["LeaveType"] = relationship()

    @property
    def employee_name(self) -> str | None:
        return self.employee.full_name if self.employee else None

    @property
    def leave_type_name(self) -> str | None:
        return self.leave_type.name if self.leave_type else None
