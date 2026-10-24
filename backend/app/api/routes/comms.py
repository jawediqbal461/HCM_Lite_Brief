from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin, require_admin_or_hr, require_any
from app.core.database import get_db
from app.schemas.comms import AnnouncementCreate, AnnouncementOut, AuditLogOut, NotificationOut
from app.services import comms_service

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


@router.get("/audit-log", response_model=list[AuditLogOut])
def audit_log(current: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return comms_service.list_audit_log(db)
