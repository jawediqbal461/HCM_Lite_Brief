from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (UniqueConstraint("month", "year", name="uq_payroll_month_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[int] = mapped_column(Integer)
    year: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | finalized
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payslips: Mapped[list["Payslip"]] = relationship(back_populates="payroll_run")


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (UniqueConstraint("payroll_run_id", "employee_id", name="uq_payslip_run_employee"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    payroll_run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)

    basic: Mapped[float] = mapped_column(Float)
    hra: Mapped[float] = mapped_column(Float)
    medical: Mapped[float] = mapped_column(Float)
    gross: Mapped[float] = mapped_column(Float)

    working_days: Mapped[int] = mapped_column(Integer)
    present_days: Mapped[float] = mapped_column(Float)
    absent_days: Mapped[float] = mapped_column(Float)
    unpaid_days: Mapped[float] = mapped_column(Float)
    half_days: Mapped[float] = mapped_column(Float)

    deductions: Mapped[float] = mapped_column(Float)
    tax: Mapped[float] = mapped_column(Float)
    net_pay: Mapped[float] = mapped_column(Float)

    payroll_run: Mapped["PayrollRun"] = relationship(back_populates="payslips")
    employee: Mapped["Employee"] = relationship()

    @property
    def employee_name(self) -> str | None:
        return self.employee.full_name if self.employee else None

    @property
    def employee_code(self) -> str | None:
        return self.employee.code if self.employee else None
