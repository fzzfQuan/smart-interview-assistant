from __future__ import annotations

from uuid import uuid4

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.models.db_models import Pin as PinModel
from app.models.schemas import PinType, PinnedItem

from config import settings


class PinStore:
    """Pin（固定）机制 — Redis 提供热数据快速读取，PostgreSQL 提供持久化存储。

    读取策略：优先查 Redis，未命中时回源到 PG。
    写入策略：同步写入 Redis 和 PG，保证数据一致性。
    """

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.redis = redis_client or aioredis.from_url(
            settings.redis_url, decode_responses=True
        )
        self._session_factory = session_factory or async_session_factory

    # ─── 内部帮助方法 ────────────────────────────────────────────────

    def _pin_key(self, user_id: str) -> str:
        """Redis Set key：存储用户的所有 pin_id。"""
        return f"user:{user_id}:pins"

    def _pin_hash_key(self, pin_id: str) -> str:
        """Redis Hash key：存储单个 Pin 的完整数据。"""
        return f"pin:{pin_id}"

    @staticmethod
    def _row_to_pinned_item(row: PinModel) -> PinnedItem:
        """将 SQLAlchemy 行对象转换为 PinnedItem。"""
        return PinnedItem(
            pin_id=str(row.pin_id),
            user_id=str(row.user_id),
            pin_type=PinType(row.pin_type),
            item_id=str(row.item_id),
            metadata=row.metadata_ or {},
            pinned_at=row.pinned_at,
        )

    # ─── 增删改查 ────────────────────────────────────────────────────

    async def pin(
        self,
        user_id: str,
        pin_type: PinType,
        item_id: str,
        metadata: dict | None = None,
    ) -> PinnedItem:
        """固定一条记录（同时写入 Redis 和 PG）。"""
        item = PinnedItem(
            pin_id=str(uuid4()),
            user_id=user_id,
            pin_type=pin_type,
            item_id=item_id,
            metadata=metadata or {},
        )
        serialized = item.model_dump(mode="json", by_alias=False)

        # 写入 Redis：Hash 存完整数据，Set 维护用户索引
        pipe = self.redis.pipeline()
        pipe.hset(self._pin_hash_key(item.pin_id), mapping=serialized)
        pipe.sadd(self._pin_key(user_id), item.pin_id)
        pipe.expire(self._pin_hash_key(item.pin_id), settings.short_term_ttl)
        await pipe.execute()

        # 写入 PG：使用 PostgreSQL UPSERT（避免重复）
        async with self._session_factory() as session:
            stmt = pg_insert(PinModel).values(
                pin_id=item.pin_id,
                user_id=user_id,
                pin_type=pin_type.value,
                item_id=item_id,
                metadata=serialized.get("metadata", {}),
            )
            stmt = stmt.on_conflict_do_nothing(
                constraint="pins_user_id_pin_type_item_id_key"
            )
            await session.execute(stmt)
            await session.commit()

        return item

    async def unpin(self, user_id: str, pin_id: str) -> bool:
        """取消固定（同时删除 Redis 和 PG 中的数据）。"""
        # 删除 Redis
        pipe = self.redis.pipeline()
        pipe.delete(self._pin_hash_key(pin_id))
        pipe.srem(self._pin_key(user_id), pin_id)
        results = await pipe.execute()

        # 删除 PG
        async with self._session_factory() as session:
            result = await session.execute(
                select(PinModel).where(
                    PinModel.pin_id == pin_id,
                    PinModel.user_id == user_id,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                await session.delete(row)
                await session.commit()
                return True

        return results[1] > 0

    async def list_pins(
        self, user_id: str, pin_type: PinType | None = None
    ) -> list[PinnedItem]:
        """列出用户的固定记录，可按类型筛选。

        读取策略：优先查 Redis，Redis 中没有则回源到 PG。
        """
        # 优先查 Redis
        pin_ids = await self.redis.smembers(self._pin_key(user_id))
        if pin_ids:
            items = []
            for pid in pin_ids:
                raw = await self.redis.hgetall(self._pin_hash_key(pid))
                if raw:
                    items.append(PinnedItem(**raw))
            if pin_type:
                items = [i for i in items if i.pin_type == pin_type]
            return sorted(items, key=lambda x: x.pinned_at, reverse=True) if items else []

        # 回源到 PG
        async with self._session_factory() as session:
            query = select(PinModel).where(PinModel.user_id == user_id)
            if pin_type:
                query = query.where(PinModel.pin_type == pin_type.value)
            query = query.order_by(PinModel.pinned_at.desc())

            result = await session.execute(query)
            rows = result.scalars().all()
            return [self._row_to_pinned_item(r) for r in rows]

    async def get_pinned_context(self, user_id: str) -> dict:
        """获取用户所有固定内容，按类型分组后用于丰富 Agent 上下文。"""
        items = await self.list_pins(user_id)
        context: dict = {}
        for item in items:
            type_key = item.pin_type.value
            if type_key not in context:
                context[type_key] = []
            context[type_key].append(item.model_dump())
        return context

    async def close(self) -> None:
        """关闭 Redis 连接。"""
        await self.redis.aclose()
