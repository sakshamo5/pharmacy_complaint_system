"""
FastAPI Application Entry Point
Configures CORS, routes, startup events, and health check.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_tables, ensure_indexes
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs create_tables() on startup so the DB schema is always ready.
    In production (Render), use Alembic migrations instead.
    """
    logger.info("Starting AIVOA Pharmacy Complaint System...")
    await create_tables()
    await ensure_indexes()
    logger.info("Database tables verified ✓")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="AI-Powered Customer Complaint Management System for Pharmaceutical QMS",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow frontend dev server + Render deployment URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check for Render deployment monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["Root"])
async def root():
    return {"message": "AIVOA Pharmacy Complaint API — see /docs for API reference"}
