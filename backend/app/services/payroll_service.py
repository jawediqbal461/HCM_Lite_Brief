import calendar
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.org import CompanySettings, LeaveType
from app.models.payroll import PayrollRun, Payslip
from app.services.attendance_service import is_weekend
from app.services.audit_service import log_action, notify
from app.services.leave_service import working_days_between

# Bonus rule: 3 lates in a month cost half a day's pay.
LATES_PER_PENALTY = 3
PENALTY_DAYS = 0.5

TAX_SLABS = [
    (0, 600_000, 0, 0.0),
    (600_000, 1_200_000, 0, 0.05),
    (1_200_000, 2_400_000, 30_000, 0.15),
    (2_400_000, 3_600_000, 210_000, 0.25),
    (3_600_000, float("inf"), 510_000, 0.35),
]


def annual_tax(annual_gross: float) -> float:
    for low, high, base, rate in TAX_SLABS:
        if low <= annual_gross < high or (high == float("inf") and annual_gross >= low):
            return base + rate * (annual_gross - low) if rate else base
    return 0.0


def _day_status(db: Session, employee_id: int, d: date, unpaid_type_ids: set[int]) -> str:
    att = db.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.date == d).first()
    if att is not None:
        return att.status
    leave = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= d,
            LeaveRequest.end_date >= d,
        )
        .first()
    )
    if leave is not None:
        return "unpaid_leave" if leave.leave_type_id in unpaid_type_ids else "on_leave"
    return "absent"


def compute_payslip_fields(db: Session, settings: CompanySettings, employee: Employee, month: int, year: int) -> dict:
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    total_working_days = working_days_between(db, settings, month_start, month_end)
    if total_working_days <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No working days in selected month")

    window_start = max(month_start, employee.date_of_joining)
    window_end = min(month_end, employee.date_of_leaving) if employee.date_of_leaving else month_end

    basic = employee.basic_salary
    hra = 0.4 * basic
    medical = 0.1 * basic
    gross = basic + hra + medical

    per_day = gross / total_working_days

    unpaid_type_ids = {lt.id for lt in db.query(LeaveType).filter(LeaveType.name == "unpaid").all()}

    absent_days = unpaid_days = half_days = late_days = 0.0
    if window_start <= window_end:
        d = window_start
        while d <= window_end:
            if not is_weekend(settings, d):
                status_ = _day_status(db, employee.id, d, unpaid_type_ids)
                if status_ == "absent":
                    absent_days += 1
                elif status_ == "unpaid_leave":
                    unpaid_days += 1
                elif status_ == "half_day":
                    half_days += 1
                elif status_ == "late":
                    late_days += 1
            d += timedelta(days=1)

    # Bonus rule from the brief: every LATES_PER_PENALTY late arrivals in the month
    # cost PENALTY_DAYS of pay. Partial groups do not count, so two lates cost nothing.
    late_penalty_days = (int(late_days) // LATES_PER_PENALTY) * PENALTY_DAYS

    employed_working_days = working_days_between(db, settings, window_start, window_end) if window_start <= window_end else 0.0
    not_employed_days = total_working_days - employed_working_days

    deduction = per_day * (not_employed_days + absent_days + unpaid_days + 0.5 * half_days + late_penalty_days)
    present_days = total_working_days - not_employed_days - absent_days - unpaid_days - half_days

    tax = annual_tax(gross * 12) / 12

    net_pay = gross - deduction - tax

    return {
        "basic": basic,
        "hra": hra,
        "medical": medical,
        "gross": gross,
        "working_days": int(total_working_days),
        "present_days": present_days,
        "absent_days": absent_days,
        "unpaid_days": unpaid_days,
        "half_days": half_days,
        "late_penalty_days": late_penalty_days,
        "deductions": deduction,
        "tax": tax,
        "net_pay": net_pay,
    }


def create_or_refresh_draft(db: Session, actor_id: int, settings: CompanySettings, month: int, year: int) -> PayrollRun:
    run = db.query(PayrollRun).filter(PayrollRun.month == month, PayrollRun.year == year).first()
    if run is not None and run.status == "finalized":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This payroll run is already finalized")
    if run is None:
        run = PayrollRun(month=month, year=year, status="draft")
        db.add(run)
        db.flush()
    else:
        db.query(Payslip).filter(Payslip.payroll_run_id == run.id).delete()

    employees = (
        db.query(Employee)
        .filter(Employee.status != "exited", Employee.date_of_joining <= date(year, month, calendar.monthrange(year, month)[1]))
        .all()
    )
    for emp in employees:
        if emp.date_of_leaving and emp.date_of_leaving < date(year, month, 1):
            continue
        fields = compute_payslip_fields(db, settings, emp, month, year)
        db.add(Payslip(payroll_run_id=run.id, employee_id=emp.id, **fields))

    db.flush()
    log_action(db, actor_id, "create", "payroll_run", run.id, after={"month": month, "year": year})
    db.commit()
    db.refresh(run)
    return run


def finalize_run(db: Session, actor_id: int, run: PayrollRun) -> PayrollRun:
    if run.status == "finalized":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already finalized")
    run.status = "finalized"
    run.finalized_at = datetime.now(timezone.utc)
    db.flush()
    log_action(db, actor_id, "finalize", "payroll_run", run.id, after={"month": run.month, "year": run.year})
    for slip in run.payslips:
        if slip.employee.user:
            notify(db, slip.employee.user.id, f"Your payslip for {run.month}/{run.year} is ready.")
    db.commit()
    db.refresh(run)
    return run
