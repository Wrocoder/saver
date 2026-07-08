from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.currency import router as currency_router
from app.api.finance import router as finance_router
from app.api.notifications import router as notifications_router
from app.api.recurring import router as recurring_router
from app.api.reports import router as reports_router
from app.api.routes import router
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Money Saver API",
    version="0.1.0",
    description="MVP API for financial goals, savings contributions, and plan projections.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(finance_router)
app.include_router(currency_router)
app.include_router(analytics_router)
app.include_router(audit_router)
app.include_router(notifications_router)
app.include_router(recurring_router)
app.include_router(reports_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "money-saver",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
