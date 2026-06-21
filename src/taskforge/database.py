import logging
from typing import AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, JSON, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from taskforge.config import settings

logger = logging.getLogger("taskforge.database")

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal: Mapped[str] = mapped_column(String, index=True, nullable=False)
    task_tree_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        default=lambda: datetime.now(timezone.utc)
    )

# Configure engine arguments.
# Connection pooling settings (pool_size, max_overflow) are ignored by SQLite but vital for PostgreSQL/MySQL
engine_args = {}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_args.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600
    })

from sqlalchemy import event

engine = create_async_engine(settings.DATABASE_URL, echo=False, **engine_args)

# SQLite WAL mode + busy_timeout configuration (MED-1)
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def init_db():
    logger.info("Initializing SQLite database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database error occurred: {str(e)}, performing rollback.")
            await session.rollback()
            raise
        finally:
            await session.close()
