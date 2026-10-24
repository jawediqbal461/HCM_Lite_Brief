"""AI tool implementations.

Every tool re-uses the same services and permission checks as the REST API, and is
scoped to the calling user's role and employee_id. No tool ever returns another
employee's salary — that stays out of the AI's reach entirely, by design.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.models.employee import Employee
from app.services import dashboard_service, leave_service
from app.services.attendance_service import employee_calendar

TOOL_DEFINITIONS = [
    {
        "name": "get_headcount",
        "description": "Get active headcount, optionally filtered by department name. Admin and HR only; not available to an Employee.",
        "input_schema": {
            "type": "object",
            "properties": {"department": {"type": "string", "description": "Department name, optional"}},
        },
    },
    {
        "name": "get_attendance_summary",
        "description": "Get attendance KPIs for a date range. For Admin/HR this covers the whole company and can be filtered by department; for an Employee it returns only their own attendance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "description": "ISO date, optional"},
                "end": {"type": "string", "description": "ISO date, optional"},
                "department": {"type": "string", "description": "Department name, optional"},
            },
        },
    },
    {
        "name": "get_late_comers",
        "description": "Get the top employees by number of late check-ins in a date range. Admin and HR only; not available to an Employee.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "limit": {"type": "integer", "description": "default 5"},
            },
        },
    },
    {
        "name": "get_leave_summary",
        "description": "Get company-wide approved leave totals by leave type for a date range. Admin and HR only; an Employee should use get_my_leave_balance instead.",
        "input_schema": {
            "type": "object",
            "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
        },
    },
    {
        "name": "get_my_leave_balance",
        "description": "Get the current employee's own leave balance by leave type for this year. Only works for the Employee role, for their own record.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_payroll_summary",
        "description": "Get aggregated payroll cost and average salary (never per-employee salary) for Admin/HR.",
        "input_schema": {
            "type": "object",
            "properties": {"month": {"type": "integer"}, "year": {"type": "integer"}},
        },
    },
    {
        "name": "search_employees",
        "description": "Search employees by name/code/email/department. Never returns salary.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def _dept_id_by_name(db: Session, name: str | None) -> int | None:
    if not name:
        return None
    from app.models.org import Department

    dept = db.query(Department).filter(Department.name.ilike(name)).first()
    return dept.id if dept else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _is_staff(user: CurrentUser) -> bool:
    return user.role in ("admin", "hr")


def _staff_only_error() -> dict:
    return {"error": "Not permitted: this covers other employees' records, and you can only see your own data."}


def get_headcount(db: Session, user: CurrentUser, department: str | None = None) -> dict:
    if not _is_staff(user):
        return _staff_only_error()
    dept_id = _dept_id_by_name(db, department)
    data = dashboard_service.hr_dashboard(db, None, None, dept_id)
    return {"headcount": data["headcount"], "department": department}


def get_attendance_summary(db: Session, user: CurrentUser, start: str | None = None, end: str | None = None, department: str | None = None) -> dict:
    end_date = _parse_date(end) or date.today()
    start_date = _parse_date(start) or (end_date - timedelta(days=30))

    if not _is_staff(user):
        if not user.employee_id:
            return _staff_only_error()
        rows = employee_calendar(db, user.employee_id, start_date, end_date)
        days_by_status: dict[str, int] = {}
        for row in rows:
            days_by_status[row.status] = days_by_status.get(row.status, 0) + 1
        return {
            "scope": "own",
            "range": {"start": str(start_date), "end": str(end_date)},
            "days_by_status": days_by_status,
            "records": len(rows),
        }

    dept_id = _dept_id_by_name(db, department)
    data = dashboard_service.hr_dashboard(db, start_date, end_date, dept_id)
    return {
        "present_today": data["present_today"],
        "on_leave_today": data["on_leave_today"],
        "late_today": data["late_today"],
        "late_pct": data["late_pct"],
        "absent_count": data["absent_count"],
        "range": data["range"],
    }


def get_late_comers(db: Session, user: CurrentUser, start: str | None = None, end: str | None = None, limit: int = 5) -> dict:
    if not _is_staff(user):
        return _staff_only_error()
    data = dashboard_service.hr_dashboard(db, _parse_date(start), _parse_date(end), None)
    return {"top_late_comers": data["top_late_comers"][: limit or 5]}


def get_leave_summary(db: Session, user: CurrentUser, start: str | None = None, end: str | None = None) -> dict:
    if not _is_staff(user):
        return _staff_only_error()
    data = dashboard_service.hr_dashboard(db, _parse_date(start), _parse_date(end), None)
    return {"leave_by_type": data["leave_by_type"]}


def get_my_leave_balance(db: Session, user: CurrentUser) -> dict:
    if user.role != "employee" or not user.employee_id:
        return {"error": "This tool only returns the signed-in employee's own balance."}
    return {"balance": leave_service.leave_balance(db, user.employee_id, date.today().year)}


def get_payroll_summary(db: Session, user: CurrentUser, month: int | None = None, year: int | None = None) -> dict:
    if user.role not in ("admin", "hr"):
        return {"error": "Not permitted."}
    data = dashboard_service.admin_dashboard(db, None, None, None)
    return {"payroll_cost": data["payroll_cost"], "avg_salary": data["avg_salary"]}


def search_employees(db: Session, user: CurrentUser, query: str) -> dict:
    if user.role not in ("admin", "hr"):
        return {"error": "Not permitted to search other employees."}
    like = f"%{query}%"
    rows = (
        db.query(Employee)
        .filter((Employee.full_name.ilike(like)) | (Employee.code.ilike(like)) | (Employee.email.ilike(like)))
        .limit(10)
        .all()
    )
    return {
        "results": [
            {
                "id": e.id,
                "code": e.code,
                "full_name": e.full_name,
                "department": e.department.name if e.department else None,
                "designation": e.designation.name if e.designation else None,
                "status": e.status,
            }
            for e in rows
        ]
    }


TOOL_IMPL = {
    "get_headcount": get_headcount,
    "get_attendance_summary": get_attendance_summary,
    "get_late_comers": get_late_comers,
    "get_leave_summary": get_leave_summary,
    "get_my_leave_balance": get_my_leave_balance,
    "get_payroll_summary": get_payroll_summary,
    "search_employees": search_employees,
}


def run_tool(db: Session, user: CurrentUser, name: str, arguments: dict) -> dict:
    fn = TOOL_IMPL.get(name)
    if fn is None:
        return {"error": f"Unknown tool {name}"}
    try:
        return fn(db, user, **arguments)
    except Exception as exc:  # defensive: never crash the chat turn on a bad tool call
        return {"error": str(exc)}
