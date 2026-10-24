import json
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.client import AIError, chat_with_tools, simple_text_completion
from app.ai.system_prompt import (
    DASHBOARD_SUMMARY_SYSTEM_PROMPT,
    SMART_LEAVE_SYSTEM_PROMPT,
    build_system_prompt,
)
from app.api.deps import CurrentUser
from app.models.comms import AILog
from app.models.org import LeaveType

RATE_LIMIT_PER_HOUR = 20


def _check_rate_limit(db: Session, user_id: int):
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = db.query(AILog).filter(AILog.user_id == user_id, AILog.created_at >= since).count()
    if count >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "AI request limit reached for this hour, please try again later")


def _log(db: Session, user_id: int, question: str, answer: str, tool_calls: list | None = None):
    entry = AILog(user_id=user_id, question=question, answer=answer, tool_calls_json=json.dumps(tool_calls, default=str) if tool_calls else None)
    db.add(entry)
    db.commit()


def chat(db: Session, user: CurrentUser, message: str) -> str:
    _check_rate_limit(db, user.id)
    system_prompt = build_system_prompt(user.role)
    try:
        answer, tool_calls = chat_with_tools(db, user, system_prompt, message)
    except AIError as exc:
        answer = f"The AI assistant is unavailable right now ({exc}). Please try again shortly."
        tool_calls = []
    _log(db, user.id, message, answer, tool_calls)
    return answer


def dashboard_summary(db: Session, user: CurrentUser, kpi_json: dict) -> list[str]:
    _check_rate_limit(db, user.id)
    try:
        text = simple_text_completion(DASHBOARD_SUMMARY_SYSTEM_PROMPT, json.dumps(kpi_json, default=str))
    except AIError as exc:
        text = f"- AI summary unavailable right now ({exc})"
    bullets = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    _log(db, user.id, f"[dashboard summary] {json.dumps(kpi_json, default=str)[:500]}", text)
    return bullets[:5] if bullets else ["No insights available right now."]


def smart_leave(db: Session, user: CurrentUser, text: str) -> dict:
    _check_rate_limit(db, user.id)
    leave_types = [lt.name for lt in db.query(LeaveType).all()]
    system_prompt = SMART_LEAVE_SYSTEM_PROMPT.format(today=date.today().isoformat(), leave_types=", ".join(leave_types))

    parsed = None
    last_error = None
    for _ in range(2):  # try once, retry once on failure
        try:
            raw = simple_text_completion(system_prompt, text)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(raw)
            break
        except (AIError, json.JSONDecodeError) as exc:
            last_error = exc
            continue

    _log(db, user.id, text, json.dumps(parsed) if parsed else f"PARSE_FAILED: {last_error}")

    if parsed is None:
        return {"leave_type_id": None, "leave_type_name": None, "start_date": None, "end_date": None, "reason": text, "raw_text": text}

    leave_type = db.query(LeaveType).filter(LeaveType.name == parsed.get("leave_type_name")).first()
    return {
        "leave_type_id": leave_type.id if leave_type else None,
        "leave_type_name": leave_type.name if leave_type else None,
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "reason": parsed.get("reason") or text,
        "raw_text": text,
    }
