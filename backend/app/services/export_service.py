"""CSV exports for the data tables.

Each export takes the same filtered query the table shows, so what downloads is
what the person is looking at — not the whole database.
"""

import csv
import io
from typing import Callable, Iterable, Sequence


def to_csv(headers: Sequence[str], rows: Iterable[Sequence]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def build(headers: Sequence[str], records: Iterable, mapper: Callable[[object], Sequence]) -> str:
    return to_csv(headers, (mapper(record) for record in records))


def attendance_csv(rows: Iterable[dict]) -> str:
    return to_csv(
        ["date", "employee_code", "employee", "department", "status", "check_in", "check_out", "source"],
        (
            [
                r["date"],
                r["employee_code"],
                r["employee_name"],
                r["department"] or "",
                r["status"],
                r["check_in_time"] or "",
                r["check_out_time"] or "",
                r["source"] or "",
            ]
            for r in rows
        ),
    )


def leave_csv(records) -> str:
    return build(
        ["employee_code", "employee", "type", "start_date", "end_date", "days", "status", "reason", "comment"],
        records,
        lambda r: [
            r.employee.code if r.employee else "",
            r.employee_name or "",
            r.leave_type_name or "",
            r.start_date,
            r.end_date,
            r.days,
            r.status,
            r.reason,
            r.approver_comment or "",
        ],
    )


def payroll_csv(run, payslips) -> str:
    return build(
        [
            "month", "year", "employee_code", "employee", "basic", "hra", "medical", "gross",
            "working_days", "present_days", "absent_days", "unpaid_days", "half_days",
            "late_penalty_days", "deductions", "tax", "net_pay",
        ],
        payslips,
        lambda p: [
            run.month, run.year,
            p.employee_code or "", p.employee_name or "",
            round(p.basic, 2), round(p.hra, 2), round(p.medical, 2), round(p.gross, 2),
            p.working_days, p.present_days, p.absent_days, p.unpaid_days, p.half_days,
            p.late_penalty_days or 0, round(p.deductions, 2), round(p.tax, 2), round(p.net_pay, 2),
        ],
    )


def audit_csv(records) -> str:
    return build(
        ["when", "actor_id", "action", "entity", "entity_id", "before", "after"],
        records,
        lambda r: [
            r.created_at.isoformat() if r.created_at else "",
            r.actor_id or "",
            r.action,
            r.entity,
            r.entity_id or "",
            r.before_json or "",
            r.after_json or "",
        ],
    )
