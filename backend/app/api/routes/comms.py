from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_admin_or_hr, require_any
from app.core.database import get_db
from app.models.comms import AuditLog
from app.schemas.comms import AnnouncementCreate, AnnouncementOut, AuditLogOut, NotificationOut
from app.schemas.common import Page, paginate
from app.services import comms_service, export_service

router = APIRouter(tags=["comms"])


@router.post("/announcements", response_model=AnnouncementOut)
def post_announcement(payload: AnnouncementCreate, current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    return comms_service.post_announcement(db, current.id, payload.title, payload.body)


@router.get("/announcements", response_model=list[AnnouncementOut])
def list_announcements(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    return comms_service.list_announcements(db)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    return comms_service.list_notifications(db, current.id)


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    comms_service.mark_notification_read(db, current.id, notification_id)
    return {"ok": True}


def _audit_query(db: Session, action: str | None, entity: str | None, actor_id: int | None, start, end):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity:
        query = query.filter(AuditLog.entity == entity)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if start:
        query = query.filter(AuditLog.created_at >= datetime.combine(start, time.min))
    if end:
        query = query.filter(AuditLog.created_at <= datetime.combine(end, time.max))
    return query.order_by(AuditLog.created_at.desc())


@router.get("/audit-log", response_model=Page[AuditLogOut])
def audit_log(
    action: str | None = None,
    entity: str | None = None,
    actor_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    page: int = 1,
    page_size: int = 50,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    items, total, page, page_size = paginate(_audit_query(db, action, entity, actor_id, start, end), page, page_size)
    return Page[AuditLogOut](items=items, total=total, page=page, page_size=page_size)


@router.get("/audit-log/export-csv", response_class=PlainTextResponse)
def audit_log_csv(
    action: str | None = None,
    entity: str | None = None,
    actor_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return export_service.audit_csv(_audit_query(db, action, entity, actor_id, start, end).all())


@router.get("/audit-log/filters")
def audit_log_filters(current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    """The actions and entities actually present, so the dropdowns never offer dead options."""
    actions = [row[0] for row in db.query(AuditLog.action).distinct().order_by(AuditLog.action)]
    entities = [row[0] for row in db.query(AuditLog.entity).distinct().order_by(AuditLog.entity)]
    return {"actions": actions, "entities": entities}
