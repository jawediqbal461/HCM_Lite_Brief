import csv
import io
from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.org import Department
from app.models.user import User
from app.services.audit_service import log_action
from app.services.auth_service import generate_temp_password
from app.core.security import hash_password


def register_employee(db: Session, actor_id: int, data: dict) -> tuple[Employee, str]:
    if db.query(Employee).filter(Employee.code == data["code"]).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Employee code already exists")
    if db.query(Employee).filter(Employee.email == data["email"]).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Employee email already exists")
    if db.query(User).filter(User.email == data["email"]).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already used for a login")
    if data.get("basic_salary", 0) <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "basic_salary must be > 0")

    employee = Employee(**data)
    db.add(employee)
    db.flush()

    temp_password = generate_temp_password()
    user = User(
        email=employee.email,
        password_hash=hash_password(temp_password),
        role="employee",
        employee_id=employee.id,
        must_change_password=True,
    )
    db.add(user)
    db.flush()

    log_action(db, actor_id, "create", "employee", employee.id, after={"code": employee.code, "email": employee.email})
    db.commit()
    db.refresh(employee)
    return employee, temp_password


def update_employee(db: Session, actor_id: int, employee: Employee, data: dict) -> Employee:
    before = {k: getattr(employee, k) for k in data if data[k] is not None}
    for k, v in data.items():
        if v is not None:
            setattr(employee, k, v)
    db.flush()
    log_action(db, actor_id, "update", "employee", employee.id, before=before, after=data)
    db.commit()
    db.refresh(employee)
    return employee


def list_employees(db: Session, search: str | None, department_id: int | None, status_: str | None, page: int, page_size: int):
    query = db.query(Employee)
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Employee.full_name.ilike(like), Employee.code.ilike(like), Employee.email.ilike(like)))
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if status_:
        query = query.filter(Employee.status == status_)
    total = query.count()
    items = query.order_by(Employee.id).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


REQUIRED_FIELDS = ["code", "full_name", "email", "department", "date_of_joining", "basic_salary"]


def csv_dry_run(db: Session, content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    results = []
    seen_codes, seen_emails = set(), set()
    dept_names = {d.name for d in db.query(Department).all()}

    for idx, row in enumerate(reader, start=2):  # header is row 1
        for field in REQUIRED_FIELDS:
            value = (row.get(field) or "").strip()
            if not value:
                results.append({"row": idx, "field": field, "reason": "required field is missing", "ok": False})
                break
        else:
            code, email, dept = row["code"].strip(), row["email"].strip(), row["department"].strip()
            if code in seen_codes or db.query(Employee).filter(Employee.code == code).first():
                results.append({"row": idx, "field": "code", "reason": "duplicate employee code", "ok": False})
                continue
            if email in seen_emails or db.query(Employee).filter(Employee.email == email).first() or "@" not in email:
                results.append({"row": idx, "field": "email", "reason": "invalid or duplicate email", "ok": False})
                continue
            if dept not in dept_names:
                results.append({"row": idx, "field": "department", "reason": "unknown department", "ok": False})
                continue
            try:
                datetime.strptime(row["date_of_joining"].strip(), "%Y-%m-%d")
            except ValueError:
                results.append({"row": idx, "field": "date_of_joining", "reason": "must be ISO date YYYY-MM-DD", "ok": False})
                continue
            try:
                salary = float(row["basic_salary"])
                if salary <= 0:
                    raise ValueError
            except ValueError:
                results.append({"row": idx, "field": "basic_salary", "reason": "must be a number > 0", "ok": False})
                continue
            seen_codes.add(code)
            seen_emails.add(email)
            results.append({"row": idx, "field": None, "reason": None, "ok": True})
            continue
        continue
    return results


def csv_import(db: Session, actor_id: int, content: bytes) -> dict:
    dry = csv_dry_run(db, content)
    if any(not r["ok"] for r in dry):
        return {"imported": 0, "errors": [r for r in dry if not r["ok"]]}

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    depts = {d.name: d.id for d in db.query(Department).all()}
    imported = 0
    for row in reader:
        register_employee(
            db,
            actor_id,
            {
                "code": row["code"].strip(),
                "full_name": row["full_name"].strip(),
                "email": row["email"].strip(),
                "department_id": depts.get(row["department"].strip()),
                "date_of_joining": datetime.strptime(row["date_of_joining"].strip(), "%Y-%m-%d").date(),
                "basic_salary": float(row["basic_salary"]),
            },
        )
        imported += 1
    return {"imported": imported, "errors": []}


def export_csv(db: Session) -> str:
    employees = db.query(Employee).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["code", "full_name", "email", "department", "designation", "date_of_joining", "status", "basic_salary"])
    for e in employees:
        writer.writerow(
            [
                e.code,
                e.full_name,
                e.email,
                e.department.name if e.department else "",
                e.designation.name if e.designation else "",
                e.date_of_joining.isoformat(),
                e.status,
                e.basic_salary,
            ]
        )
    return buf.getvalue()
