from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin_or_hr, require_any
from app.core.database import get_db
from app.schemas.ai import ChatRequest, ChatResponse, SummaryRequest, SummaryResponse
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, current: CurrentUser = Depends(require_any), db: Session = Depends(get_db)):
    answer = ai_service.chat(db, current, payload.message)
    return ChatResponse(answer=answer)


@router.post("/summarize", response_model=SummaryResponse)
def summarize(payload: SummaryRequest, current: CurrentUser = Depends(require_admin_or_hr), db: Session = Depends(get_db)):
    bullets = ai_service.dashboard_summary(db, current, payload.kpi_json)
    return SummaryResponse(bullets=bullets)
