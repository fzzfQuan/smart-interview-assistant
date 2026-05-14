from __future__ import annotations

from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from app.agents.prompts import (
    DEFAULT_JOB_REQUIREMENTS,
    MATCHING_ANALYST_SYSTEM,
    MATCHING_ANALYST_USER,
)
from app.agents.state import AgentState
from app.models.schemas import MatchReport
from config import settings


@lru_cache(1)
def _get_llm() -> ChatDeepSeek:
    """懒加载 LLM 实例（带缓存），避免无 API Key 时导入报错。"""
    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        temperature=0.2,
    )


def _build_pinned_hint(state: AgentState) -> str:
    """根据用户已固定的内容，构造提示信息注入给 LLM。"""
    ctx = state.get("pinned_context") or {}
    hints = []
    if "job_description" in ctx:
        hints.append("提示：用户固定了职位描述——请将其作为额外参考。")
    if "analysis_report" in ctx:
        hints.append("提示：用户固定了之前的分析报告可供对比参考。")
    return "\n".join(hints)


async def analyze_match_node(state: AgentState) -> dict:
    """匹配分析节点：将简历与职位要求对比，生成匹配报告。"""
    if not state.get("parsed_resume"):
        return {
            "errors": ["匹配分析失败：缺少结构化简历数据"],
            "progress": {"stage": "analyze", "percentage": 65, "message": "匹配分析失败：缺少简历数据"},
        }

    job_req = state.get("job_requirements") or DEFAULT_JOB_REQUIREMENTS
    pinned_hint = _build_pinned_hint(state)
    user_msg = MATCHING_ANALYST_USER.format(
        parsed_resume=state["parsed_resume"],
        job_requirements=job_req,
        pinned_context_hint=pinned_hint,
    )

    try:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(MatchReport)
        result: MatchReport = await structured_llm.ainvoke([
            ("system", MATCHING_ANALYST_SYSTEM),
            ("human", user_msg),
        ])
        return {
            "match_analysis": result.model_dump(mode="json"),
            "progress": {"stage": "analyze", "percentage": 65, "message": "匹配分析完成"},
            "agent_traces": [{"node": "analyze_match", "status": "ok"}],
        }
    except Exception as e:
        return {
            "errors": [f"匹配分析失败：{e}"],
            "progress": {"stage": "analyze", "percentage": 65, "message": "匹配分析失败"},
            "agent_traces": [{"node": "analyze_match", "status": "error", "error": str(e)}],
        }
