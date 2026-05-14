from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# 枚举定义
# ═══════════════════════════════════════════════════════════════════════

class PinType(str, Enum):
    """固定（Pin）的类型：简历、职位描述、分析报告、面试题、自定义备注。"""
    resume = "resume"
    job_description = "job_description"
    analysis_report = "analysis_report"
    interview_questions = "interview_questions"
    custom_note = "custom_note"


class SkillCategory(str, Enum):
    """技能分类：编程语言、框架、工具、软技能、领域知识。"""
    language = "language"
    framework = "framework"
    tool = "tool"
    soft = "soft"
    domain = "domain"


class QuestionDifficulty(str, Enum):
    """面试题难度等级：基础、进阶、深入。"""
    basic = "basic"
    intermediate = "intermediate"
    advanced = "advanced"


class QuestionType(str, Enum):
    """面试题类型：技术题、行为题、项目深挖。"""
    technical = "technical"
    behavioral = "behavioral"
    project_deep_dive = "project_deep_dive"


# ═══════════════════════════════════════════════════════════════════════
# 简历相关模型
# ═══════════════════════════════════════════════════════════════════════

class Skill(BaseModel):
    """单个技能。"""
    name: str
    category: SkillCategory
    proficiency: float | None = None  # 熟练度，范围 0-1，从简历中估算


class Experience(BaseModel):
    """工作经历。"""
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    achievements: list[str] = []        # 关键成就
    skills_used: list[str] = []         # 用到的技能


class Education(BaseModel):
    """教育背景。"""
    institution: str
    degree: str
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class Project(BaseModel):
    """项目经历。"""
    name: str
    description: str
    technologies: list[str] = []
    highlights: list[str] = []


class PersonalInfo(BaseModel):
    """个人信息。"""
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None       # 求职意向 / 当前职位
    summary: str | None = None      # 个人总结


class ResumeSchema(BaseModel):
    """完整的结构化简历数据。"""
    personal_info: PersonalInfo
    skills: list[Skill] = []
    experiences: list[Experience] = []
    education: list[Education] = []
    projects: list[Project] = []


# ═══════════════════════════════════════════════════════════════════════
# 匹配分析模型
# ═══════════════════════════════════════════════════════════════════════

class CategoryScore(BaseModel):
    """某一技能分类的匹配得分。"""
    category: SkillCategory
    score: float                      # 匹配度 0-1
    matched: list[str]                # 已匹配的技能
    missing: list[str]                # 缺失的技能


class MatchReport(BaseModel):
    """简历与职位的完整匹配分析报告。"""
    overall_score: float              # 总体匹配度 0-1
    category_scores: list[CategoryScore] = []
    strengths: list[str] = []         # 优势项
    gaps: list[str] = []              # 短板 / 差距
    experience_years: float | None = None  # 经验年限
    summary: str | None = None        # 总结评语


# ═══════════════════════════════════════════════════════════════════════
# 面试题模型
# ═══════════════════════════════════════════════════════════════════════

class Question(BaseModel):
    """一道面试题。"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: QuestionType
    difficulty: QuestionDifficulty
    content: str                      # 题目内容
    rationale: str | None = None      # 出题理由（为什么问这道题）
    reference_answer: str | None = None  # 参考答案 / 考察要点


class InterviewQuestions(BaseModel):
    """完整的面试题集合，按类型分组。"""
    technical: list[Question] = []         # 技术题
    behavioral: list[Question] = []        # 行为题
    project_deep_dive: list[Question] = [] # 项目深挖题

    @property
    def all_questions(self) -> list[Question]:
        """获取所有题目（合并三种类型）。"""
        return self.technical + self.behavioral + self.project_deep_dive


# ═══════════════════════════════════════════════════════════════════════
# 记忆 / 持久化模型
# ═══════════════════════════════════════════════════════════════════════

class PinnedItem(BaseModel):
    """一条被固定的记录。"""
    pin_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    pin_type: PinType
    item_id: str
    metadata: dict = {}              # 额外信息：标签、备注等
    pinned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserProfile(BaseModel):
    """用户面试画像，记录跨面试的聚合数据。"""
    user_id: str
    aggregated_skills: dict = {}     # 技能聚合
    experience_summary: str | None = None
    interview_count: int = 0          # 面试次数
    avg_match_score: float = 0.0      # 平均匹配度
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InterviewSessionRecord(BaseModel):
    """一次面试会话的记录。"""
    session_id: str
    user_id: str
    resume_id: str | None = None
    job_description: str | None = None
    match_report: dict | None = None
    questions: dict | None = None
    feedback: dict | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════
# API 请求 / 响应模型
# ═══════════════════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    """上传简历后的完整分析结果。"""
    session_id: str
    parsed_resume: ResumeSchema
    match_analysis: MatchReport
    interview_questions: InterviewQuestions


# ═══════════════════════════════════════════════════════════════════════
# 认证相关模型
# ═══════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """用户注册请求。"""
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=255)
    display_name: str | None = None


class LoginRequest(BaseModel):
    """用户登录请求。"""
    username: str = Field(..., max_length=100)
    password: str = Field(..., max_length=255)


class TokenResponse(BaseModel):
    """登录成功返回的令牌。"""
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    """用户公开信息。"""
    id: str
    username: str
    email: str
    display_name: str | None = None
    is_active: bool = True
    created_at: str | None = None


class PinRequest(BaseModel):
    """固定一条记录的请求。"""
    user_id: str
    pin_type: PinType
    item_id: str
    metadata: dict = {}


class PinResponse(BaseModel):
    """固定操作的响应。"""
    pin: PinnedItem


class PinListResponse(BaseModel):
    """固定列表的响应。"""
    pins: list[PinnedItem]


class SessionResponse(BaseModel):
    """会话状态查询的响应。"""
    session_id: str
    state: dict


class UserProfileResponse(BaseModel):
    """用户画像查询的响应。"""
    profile: UserProfile
