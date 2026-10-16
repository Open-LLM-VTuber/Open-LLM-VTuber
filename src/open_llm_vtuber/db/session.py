"""Database session management."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from .models import Base

# Global engine and session factory
_engine = None
_session_factory = None


def get_database_url() -> str:
    """Get database URL from environment or default."""
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/vtuber.db")


async def init_db(database_url: Optional[str] = None) -> None:
    """Initialize database engine and create tables."""
    global _engine, _session_factory
    
    if database_url is None:
        database_url = get_database_url()
    
    # Ensure data directory exists for SQLite
    if database_url.startswith("sqlite"):
        db_path = database_url.replace("sqlite+aiosqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    _engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
    )
    
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager."""
    if _session_factory is None:
        await init_db()
    
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session() -> AsyncSession:
    """Get a database session (for manual management)."""
    if _session_factory is None:
        await init_db()
    return _session_factory()