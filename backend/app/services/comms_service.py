from sqlalchemy.orm import Session

from app.models.comms import Announcement, AuditLog, Notification
from app.services.audit_service import log_action


def post_announcement(db: Session, actor_id: int, title: str, body: str) -> Announcement:
    ann = Announcement(title=title, body=body, posted_by=actor_id)
    db.add(ann)
    db.flush()
    log_action(db, actor_id, "create", "announcement", ann.id, after={"title": title})
    db.commit()
    db.refresh(ann)
    return ann


def list_announcements(db: Session, limit: int = 20):
    return db.query(Announcement).order_by(Announcement.created_at.desc()).limit(limit).all()


def list_notifications(db: Session, user_id: int, limit: int = 20):
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(limit).all()


def mark_notification_read(db: Session, user_id: int, notification_id: int):
    note = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if note:
        note.read = True
        db.commit()
    return note


def list_audit_log(db: Session, limit: int = 100):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
