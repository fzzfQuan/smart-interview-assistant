from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory, init_db, close_db
from app.memory.long_term import LongTermMemory
from app.memory.pin_store import PinStore
from app.memory.short_term import ShortTermMemory
from app.models.schemas import MatchReport, ResumeSchema


class MemoryManager:
    """统一的记忆系统接口，供 Agent 调用。

    协调三个子系统：
    - ShortTermMemory（Redis）— 会话状态、消息历史、缓存
    - LongTermMemory（PostgreSQL / SQLAlchemy）— 用户画像、面试记录、技能记录
    - PinStore（Redis + PG）— 固定（Pin）的关键信息
    """

    def __init__(
        self,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        pin_store: PinStore | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        sf = session_factory or async_session_factory
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory(sf)
        self.pins = pin_store or PinStore(session_factory=sf)

    # ─── 会话（短期记忆） ────────────────────────────────────────────

    async def save_session_state(self, session_id: str, state: dict) -> None:
        """保存会话状态到 Redis。"""
        await self.short_term.set_state(session_id, state)

    async def get_session_state(self, session_id: str) -> dict | None:
        """从 Redis 恢复会话状态。"""
        return await self.short_term.get_state(session_id)

    async def add_session_message(
        self, session_id: str, role: str, content: str
    ) -> None:
        """向会话的消息历史中添加一条记录。"""
        await self.short_term.add_message(session_id, role, content)

    async def get_session_messages(self, session_id: str) -> list[dict]:
        """获取会话的消息历史。"""
        return await self.short_term.get_messages(session_id)

    # ─── 长期持久化 ─────────────────────────────────────────────────

    async def save_interview_result(
        self,
        session_id: str,
        user_id: str,
        resume_id: str | None,
        job_description: str | None,
        parsed_resume: ResumeSchema,
        match_report: MatchReport,
        questions: dict,
    ) -> None:
        """保存一次完整的面试分析结果。

        同时更新：
        1. 面试会话记录（interview_sessions 表）
        2. 用户画像（user_profiles 表）— 技能合并、次数累加、平均分更新
        3. 技能记录（skill_records 表）— 取最高熟练度
        4. 活跃会话列表（Redis）
        """
        # 保存面试会话
        await self.long_term.save_interview_session(
            session_id,
            {
                "session_id": session_id,
                "user_id": user_id,
                "resume_id": resume_id,
                "job_description": job_description,
                "match_report": match_report.model_dump(mode="json"),
                "questions": questions,
            },
        )

        # 更新用户画像
        skills = {
            s.name: {"category": s.category.value, "proficiency": s.proficiency or 0.5}
            for s in parsed_resume.skills
        }
        existing = await self.long_term.get_user_profile(user_id)
        if existing:
            merged = existing["aggregated_skills"]
            merged.update(skills)
            count = existing["interview_count"] + 1
            avg = (
                (existing["avg_match_score"] * (count - 1) + match_report.overall_score)
                / count
            )
        else:
            merged = skills
            count = 1
            avg = match_report.overall_score

        await self.long_term.upsert_user_profile(
            user_id,
            {
                "aggregated_skills": merged,
                "experience_summary": parsed_resume.personal_info.summary,
                "interview_count": count,
                "avg_match_score": avg,
            },
        )

        # 保存每项技能记录
        for skill in parsed_resume.skills:
            await self.long_term.upsert_skill(
                user_id, skill.name, skill.category.value, skill.proficiency or 0.5
            )

        # 记录活跃会话
        await self.short_term.add_active_session(user_id, session_id)

    async def get_user_profile(self, user_id: str) -> dict | None:
        """获取用户面试画像。"""
        return await self.long_term.get_user_profile(user_id)

    async def get_user_sessions(self, user_id: str, limit: int = 20) -> list[dict]:
        """获取用户的面试历史记录。"""
        return await self.long_term.get_user_sessions(user_id, limit)

    # ─── Pin（固定） ─────────────────────────────────────────────────

    async def pin_item(
        self, user_id: str, pin_type: str, item_id: str, metadata: dict | None = None
    ):
        """固定一条关键信息（简历 / JD / 分析报告 / 面试题）。"""
        from app.models.schemas import PinType

        return await self.pins.pin(user_id, PinType(pin_type), item_id, metadata)

    async def unpin_item(self, user_id: str, pin_id: str) -> bool:
        """取消固定。"""
        return await self.pins.unpin(user_id, pin_id)

    async def list_pins(self, user_id: str, pin_type: str | None = None):
        """列出固定的记录，可按类型筛选。"""
        from app.models.schemas import PinType

        pt = PinType(pin_type) if pin_type else None
        return await self.pins.list_pins(user_id, pt)

    async def get_pinned_context(self, user_id: str) -> dict:
        """获取所有固定内容，按类型分组后供 Agent 使用。"""
        return await self.pins.get_pinned_context(user_id)

    # ─── 生命周期 ────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """初始化数据库表结构（应用启动时调用）。"""
        await init_db()

    async def close(self) -> None:
        """释放所有连接（应用关闭时调用）。"""
        await self.short_term.close()
        await self.long_term.close()
        await self.pins.close()
        await close_db()
