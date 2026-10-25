from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai, attendance, auth, comms, dashboards, employees, leave, org, payroll
from app.core.config import settings
from app.core.database import Base, engine, ensure_additive_columns
from app import models  # noqa: F401 — registers all models on Base before create_all

app = FastAPI(title="HCM Lite API", version="0.1.0")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    added = ensure_additive_columns()
    if added:
        print(f"Added missing columns: {', '.join(added)}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(org.router)
app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(leave.router)
app.include_router(payroll.router)
app.include_router(dashboards.router)
app.include_router(ai.router)
app.include_router(comms.router)


@app.get("/health")
def health():
    return {"status": "ok"}
