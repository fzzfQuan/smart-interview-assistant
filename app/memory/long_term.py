from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql import func

from app.database import async_session_factory
from app.models.db_models import (
    InterviewSession as InterviewSessionModel,
    SkillRecord as SkillRecordModel,
    UserProfile as UserProfileModel,
)


class LongTermMemory:
    """基于 PostgreSQL 的长期记忆（SQLAlchemy ORM 实现）。

    数据表：
    - user_profiles — 用户面试画像（技能聚合、面试次数、平均匹配度）
    - interview_sessions — 多轮面试记录
    - pins — 用户固定的关键信息
    - skill_records — 技能标签索引
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory or async_session_factory

    # ─── 用户画像 ────────────────────────────────────────────────────

    async def get_user_profile(self, user_id: str) -> dict | None:
        """获取用户面试画像。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return {
                "user_id": str(row.user_id),
                "aggregated_skills": row.aggregated_skills or {},
                "experience_summary": row.experience_summary,
                "interview_count": row.interview_count,
                "avg_match_score": row.avg_match_score,
                "updated_at": row.updated_at,
            }

    async def upsert_user_profile(self, user_id: str, data: dict) -> None:
        """创建或更新用户面试画像（PostgreSQL UPSERT）。"""
        async with self._session_factory() as session:
            stmt = pg_insert(UserProfileModel).values(
                user_id=user_id,
                aggregated_skills=data.get("aggregated_skills", {}),
                experience_summary=data.get("experience_summary"),
                interview_count=data.get("interview_count", 0),
                avg_match_score=data.get("avg_match_score", 0.0),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="user_profiles_pkey",
                set_={
                    "aggregated_skills": stmt.excluded.aggregated_skills,
                    "experience_summary": stmt.excluded.experience_summary,
                    "interview_count": stmt.excluded.interview_count,
                    "avg_match_score": stmt.excluded.avg_match_score,
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)
            await session.commit()

    # ─── 面试记录 ────────────────────────────────────────────────────

    async def save_interview_session(self, session_id: str, data: dict) -> None:
        """保存一次面试会话记录（不存在则插入，存在则更新）。"""
        async with self._session_factory() as session:
            stmt = pg_insert(InterviewSessionModel).values(
                session_id=session_id,
                user_id=data["user_id"],
                resume_id=data.get("resume_id"),
                job_description=data.get("job_description"),
                match_report=data.get("match_report"),
                questions=data.get("questions"),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="interview_sessions_pkey",
                set_={
                    "match_report": stmt.excluded.match_report,
                    "questions": stmt.excluded.questions,
                },
            )
            await session.execute(stmt)
            await session.commit()

    async def get_user_sessions(
        self, user_id: str, limit: int = 20
    ) -> list[dict]:
        """获取用户的面试记录列表（按时间倒序）。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(InterviewSessionModel)
                .where(InterviewSessionModel.user_id == user_id)
                .order_by(InterviewSessionModel.created_at.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "session_id": str(r.session_id),
                    "user_id": str(r.user_id),
                    "resume_id": str(r.resume_id) if r.resume_id else None,
                    "job_description": r.job_description,
                    "match_report": r.match_report,
                    "questions": r.questions,
                    "feedback": r.feedback,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    # ─── 技能记录 ────────────────────────────────────────────────────

    async def upsert_skill(
        self, user_id: str, skill_name: str, category: str, proficiency: float
    ) -> None:
        """记录或更新技能（重复出现时增加计数、取最高熟练度）。"""
        async with self._session_factory() as session:
            stmt = pg_insert(SkillRecordModel).values(
                user_id=user_id,
                skill_name=skill_name,
                category=category,
                proficiency=proficiency,
                encounter_count=1,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="skill_records_user_id_skill_name_key",
                set_={
                    "encounter_count": SkillRecordModel.encounter_count + 1,
                    "proficiency": func.greatest(
                        SkillRecordModel.proficiency, proficiency
                    ),
                    "last_seen_at": func.now(),
                },
            )
            await session.execute(stmt)
            await session.commit()

    async def get_user_skills(self, user_id: str) -> list[dict]:
        """获取用户的技能记录（按熟练度倒序）。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(SkillRecordModel)
                .where(SkillRecordModel.user_id == user_id)
                .order_by(SkillRecordModel.proficiency.desc())
            )
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "user_id": str(r.user_id),
                    "skill_name": r.skill_name,
                    "category": r.category,
                    "proficiency": r.proficiency,
                    "encounter_count": r.encounter_count,
                    "last_seen_at": r.last_seen_at,
                }
                for r in rows
            ]

    async def close(self) -> None:
        """LongTermMemory 不持有引擎，由 app/database.py 统一管理。"""
        pass
