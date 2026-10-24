from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)

    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    designation_id: Mapped[int | None] = mapped_column(ForeignKey("designations.id"), nullable=True)

    date_of_joining: Mapped[date] = mapped_column(Date)
    date_of_leaving: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | probation | exited

    basic_salary: Mapped[float] = mapped_column(Float, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="employee", foreign_keys="User.employee_id", uselist=False)
    department: Mapped["Department"] = relationship()
    designation: Mapped["Designation"] = relationship()
