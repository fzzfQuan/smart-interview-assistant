from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict):
    """Agent 的共享状态，在 LangGraph 各节点之间流转。

    每个节点（Node）从这个状态中读取数据，处理后写回。
    Supervisor 负责编排各节点的执行顺序。
    """

    # ── 简历数据 ──
    raw_text: str                              # 简历的原始文本
    parsed_resume: dict | None                 # 结构化简历（ResumeSchema 的字典形式）

    # ── 职位要求（可选，用户提供） ──
    job_requirements: str | None

    # ── 匹配分析 ──
    match_analysis: dict | None                # 匹配分析报告（MatchReport 的字典形式）

    # ── 面试题 ──
    interview_questions: dict | None           # 面试题集合（InterviewQuestions 的字典形式）

    # ── 会话 / 用户标识 ──
    session_id: str
    user_id: str

    # ── 记忆：启动时从 Pin 加载的上下文 ──
    pinned_context: dict | None

    # ── 执行过程中捕获的错误 ──
    errors: list[str]

    # ── 执行进度（用于流式输出和进度展示） ──
    progress: dict | None              # {"stage": str, "percentage": int, "message": str}

    # ── Agent 执行轨迹（用于可观测性和调试） ──
    agent_traces: list[dict[str, Any]]
