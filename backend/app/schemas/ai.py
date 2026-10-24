from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    ai_generated: bool = True


class SummaryRequest(BaseModel):
    kpi_json: dict


class SummaryResponse(BaseModel):
    bullets: list[str]
    ai_generated: bool = True
