from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """用户账号表。"""

    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserProfile(Base):
    """用户面试画像表。"""

    __tablename__ = "user_profiles"

    user_id = Column(UUID, primary_key=True)
    aggregated_skills = Column(JSONB, default={}, nullable=False)
    experience_summary = Column(Text, nullable=True)
    interview_count = Column(Integer, default=0, nullable=False)
    avg_match_score = Column(Float, default=0.0, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    interview_sessions = relationship("InterviewSession", back_populates="user")
    skill_records = relationship("SkillRecord", back_populates="user")


class InterviewSession(Base):
    """多轮面试记录表。"""

    __tablename__ = "interview_sessions"

    session_id = Column(UUID, primary_key=True)
    user_id = Column(
        UUID, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False
    )
    resume_id = Column(UUID, nullable=True)
    job_description = Column(Text, nullable=True)
    match_report = Column(JSONB, nullable=True)
    questions = Column(JSONB, nullable=True)
    feedback = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("UserProfile", back_populates="interview_sessions")

    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
    )


class Pin(Base):
    """用户固定（Pin）的关键信息表。"""

    __tablename__ = "pins"

    pin_id = Column(UUID, primary_key=True)
    user_id = Column(UUID, nullable=False, index=True)
    pin_type = Column(String(50), nullable=False)
    item_id = Column(UUID, nullable=False)
    metadata_ = Column("metadata", JSONB, default={}, nullable=False)
    pinned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_pins_user", "user_id"),
        UniqueConstraint("user_id", "pin_type", "item_id"),
    )


class SkillRecord(Base):
    """技能标签索引表，用于跨会话的技能聚合分析。"""

    __tablename__ = "skill_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False
    )
    skill_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)
    proficiency = Column(Float, default=0.0, nullable=False)
    encounter_count = Column(Integer, default=1, nullable=False)
    last_seen_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("UserProfile", back_populates="skill_records")

    __table_args__ = (
        UniqueConstraint("user_id", "skill_name"),
        Index("idx_skill_records_user", "user_id"),
    )
