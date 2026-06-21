import logging
from typing import AsyncGenerator
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from taskforge.config import settings

logger = logging.getLogger("taskforge.database")

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal: Mapped[str] = mapped_column(String, nullable=False)
    task_tree_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

# Create engine and async session maker
engine = create_async_engine(settings.DATABASE_URL, echo=False)
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
