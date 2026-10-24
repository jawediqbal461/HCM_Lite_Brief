from datetime import date, time

from sqlalchemy import Date, Float, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Designation(Base):
    __tablename__ = "designations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class LeaveType(Base):
    __tablename__ = "leave_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # annual | sick | casual | unpaid
    annual_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(150))


class CompanySettings(Base):
    """Singleton row (id=1) created during first-run setup."""

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    office_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    grace_minutes: Mapped[int] = mapped_column(Integer, default=15)
    half_day_hours: Mapped[float] = mapped_column(Float, default=5.0)
    weekend_days: Mapped[str] = mapped_column(String(20), default="5,6")  # Mon=0..Sun=6, default Sat,Sun
    office_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    office_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    office_radius_m: Mapped[int] = mapped_column(Integer, default=150)
