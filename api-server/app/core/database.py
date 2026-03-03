from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


_sync_engine = None
_sync_session_factory = None


def get_sync_engine():
    """同步数据库引擎，供 Celery worker 使用（延迟初始化）。"""
    global _sync_engine
    if _sync_engine is None:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
        _sync_engine = create_engine(sync_url, pool_size=5, pool_pre_ping=True)
    return _sync_engine


def get_sync_session_factory():
    """同步会话工厂，供 Celery worker 使用（延迟初始化，缓存实例）。"""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(bind=get_sync_engine())
    return _sync_session_factory
