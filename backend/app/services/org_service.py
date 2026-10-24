from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.org import CompanySettings, Department, Designation, Holiday, LeaveType
from app.services.audit_service import log_action


def get_settings(db: Session) -> CompanySettings:
    row = db.query(CompanySettings).first()
    if row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Company not set up yet")
    return row


def update_settings(db: Session, actor_id: int, data: dict) -> CompanySettings:
    row = get_settings(db)
    before = {k: getattr(row, k) for k in data}
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    db.flush()
    log_action(db, actor_id, "update", "company_settings", row.id, before=before, after=data)
    db.commit()
    db.refresh(row)
    return row


def create_department(db: Session, actor_id: int, name: str) -> Department:
    if db.query(Department).filter(Department.name == name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Department already exists")
    dept = Department(name=name)
    db.add(dept)
    db.flush()
    log_action(db, actor_id, "create", "department", dept.id, after={"name": name})
    db.commit()
    db.refresh(dept)
    return dept


def create_designation(db: Session, actor_id: int, name: str) -> Designation:
    if db.query(Designation).filter(Designation.name == name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Designation already exists")
    desig = Designation(name=name)
    db.add(desig)
    db.flush()
    log_action(db, actor_id, "create", "designation", desig.id, after={"name": name})
    db.commit()
    db.refresh(desig)
    return desig


def create_leave_type(db: Session, actor_id: int, name: str, annual_quota: int | None) -> LeaveType:
    if db.query(LeaveType).filter(LeaveType.name == name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Leave type already exists")
    lt = LeaveType(name=name, annual_quota=annual_quota)
    db.add(lt)
    db.flush()
    log_action(db, actor_id, "create", "leave_type", lt.id, after={"name": name, "annual_quota": annual_quota})
    db.commit()
    db.refresh(lt)
    return lt


def create_holiday(db: Session, actor_id: int, date_, name: str) -> Holiday:
    if db.query(Holiday).filter(Holiday.date == date_).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Holiday already exists on that date")
    h = Holiday(date=date_, name=name)
    db.add(h)
    db.flush()
    log_action(db, actor_id, "create", "holiday", h.id, after={"date": str(date_), "name": name})
    db.commit()
    db.refresh(h)
    return h


def seed_default_leave_types(db: Session, actor_id: int):
    defaults = [("annual", 14), ("sick", 8), ("casual", 10), ("unpaid", None)]
    for name, quota in defaults:
        if not db.query(LeaveType).filter(LeaveType.name == name).first():
            db.add(LeaveType(name=name, annual_quota=quota))
    db.commit()
