from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import settings

from config import settings

# ── 异步引擎 ─────────────────────────────────────────────────────────
# SQLAlchemy 需要 asyncpg 作为驱动，将 pg_dsn 中的 postgresql:// 替换为 postgresql+asyncpg://
_async_dsn = settings.pg_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    _async_dsn,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)

# ── 会话工厂 ─────────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有模型继承自此类。"""
    pass


async def init_db() -> None:
    """创建所有表结构（如果不存在）。"""
    from app.models.db_models import InterviewSession, Pin, SkillRecord, User, UserProfile  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库引擎，释放连接池。"""
    await engine.dispose()


async def get_session() -> AsyncSession:
    """获取一个新的异步会话（用于依赖注入）。"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
