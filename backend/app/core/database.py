from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings


# Create async engine — asyncpg driver for PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory — expire_on_commit=False prevents detached instance errors
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables — used during app startup in development."""
    async with engine.begin() as conn:
        from app.models import complaint, risk_assessment, audit_log  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def ensure_indexes():
    """
    Idempotently create indexes on existing tables.
    create_all() only creates indexes for NEW tables — this backfills the
    current dev DB. Safe to call every startup (IF NOT EXISTS).
    """
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_complaints_thread_id ON complaints (thread_id)",
        "CREATE INDEX IF NOT EXISTS ix_complaints_product_date ON complaints (product_name, complaint_date)",
    ]
    async with engine.begin() as conn:
        for stmt in statements:
            await conn.execute(text(stmt))
