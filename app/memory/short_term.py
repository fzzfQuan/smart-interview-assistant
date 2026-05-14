from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from config import settings


class ShortTermMemory:
    """基于 Redis 的短期记忆，所有数据带 TTL 自动过期。

    用途：
    - 会话状态快照（session state）
    - Agent 对话历史（message history）
    - LLM 调用结果缓存（cache）
    - 活跃会话列表（active sessions）
    """

    def __init__(self, client: aioredis.Redis | None = None):
        self.client = client or aioredis.from_url(
            settings.redis_url, decode_responses=True
        )

    async def set_state(self, session_id: str, state: dict) -> None:
        """保存会话状态快照。"""
        await self.client.setex(
            f"session:{session_id}:state",
            settings.short_term_ttl,
            json.dumps(state, default=str),
        )

    async def get_state(self, session_id: str) -> dict | None:
        """获取会话状态快照。"""
        raw = await self.client.get(f"session:{session_id}:state")
        return json.loads(raw) if raw else None

    async def delete_state(self, session_id: str) -> None:
        """删除会话状态快照。"""
        await self.client.delete(f"session:{session_id}:state")

    async def add_message(
        self, session_id: str, role: str, content: str, max_messages: int = 50
    ) -> None:
        """追加一条 Agent 对话消息，超过上限时自动裁剪旧消息。"""
        key = f"session:{session_id}:messages"
        msg = json.dumps({"role": role, "content": content}, default=str)
        await self.client.rpush(key, msg)
        await self.client.ltrim(key, -max_messages, -1)
        await self.client.expire(key, settings.short_term_ttl)

    async def get_messages(self, session_id: str) -> list[dict]:
        """获取会话的消息历史。"""
        raw = await self.client.lrange(f"session:{session_id}:messages", 0, -1)
        return [json.loads(m) for m in raw] if raw else []

    async def cache_get(self, key: str) -> str | None:
        """读取缓存。"""
        return await self.client.get(f"cache:{key}")

    async def cache_set(self, key: str, value: str, ttl: int | None = None) -> None:
        """写入缓存（带 TTL）。"""
        await self.client.setex(
            f"cache:{key}", ttl or settings.cache_ttl, value
        )

    async def add_active_session(self, user_id: str, session_id: str) -> None:
        """记录用户的活跃会话。"""
        await self.client.sadd(f"user:{user_id}:active_sessions", session_id)
        await self.client.expire(f"user:{user_id}:active_sessions", settings.short_term_ttl)

    async def get_active_sessions(self, user_id: str) -> list[str]:
        """获取用户的活跃会话列表。"""
        return list(await self.client.smembers(f"user:{user_id}:active_sessions") or [])

    async def close(self) -> None:
        """关闭 Redis 连接。"""
        await self.client.aclose()
