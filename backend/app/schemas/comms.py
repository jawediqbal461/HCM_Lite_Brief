from datetime import datetime

from pydantic import BaseModel


class AnnouncementCreate(BaseModel):
    title: str
    body: str


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str
    posted_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    message: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    actor_id: int | None
    action: str
    entity: str
    entity_id: int | None
    before_json: str | None
    after_json: str | None
    created_at: datetime

    class Config:
        from_attributes = True
