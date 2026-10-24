import json

from sqlalchemy.orm import Session

from app.models.comms import AuditLog, Notification


def log_action(
    db: Session,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None,
    before: dict | None = None,
    after: dict | None = None,
):
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before_json=json.dumps(before, default=str) if before else None,
        after_json=json.dumps(after, default=str) if after else None,
    )
    db.add(entry)
    db.flush()
    return entry


def notify(db: Session, user_id: int, message: str):
    note = Notification(user_id=user_id, message=message)
    db.add(note)
    db.flush()
    return note
