from __future__ import annotations

from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from app.agents.prompts import QUESTION_GENERATOR_SYSTEM, QUESTION_GENERATOR_USER
from app.agents.state import AgentState
from app.models.schemas import InterviewQuestions
from config import settings


@lru_cache(1)
def _get_llm() -> ChatDeepSeek:
    """懒加载 LLM 实例（带缓存），避免无 API Key 时导入报错。"""
    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base="https://api.deepseek.com",
        temperature=0.1,
        model_kwargs={
            "tool_choice": "auto",
        },
        extra_body={"thinking": {"type": "disabled"}},
    )


def _build_pinned_hint(state: AgentState) -> str:
    """根据用户已固定的内容，构造提示信息注入给 LLM。"""
    ctx = state.get("pinned_context") or {}
    hints = []
    if "interview_questions" in ctx:
        hints.append(
            "提示：用户固定了之前的面试题——请避免重复，并在之前的基础上深化。"
        )
    if "resume" in ctx:
        hints.append("提示：用户固定了简历——可参考其中的内容提问。")
    return "\n".join(hints)


async def generate_questions_node(state: AgentState) -> dict:
    """面试出题节点：根据简历和匹配分析结果定制面试题。"""
    if not state.get("parsed_resume"):
        return {
            "errors": ["面试出题失败：缺少结构化简历数据"],
            "progress": {"stage": "generate", "percentage": 85, "message": "面试题生成失败：缺少简历数据"},
        }
    if not state.get("match_analysis"):
        return {
            "errors": ["面试出题失败：缺少匹配分析报告"],
            "progress": {"stage": "generate", "percentage": 85, "message": "面试题生成失败：缺少匹配分析"},
        }

    pinned_hint = _build_pinned_hint(state)
    user_msg = QUESTION_GENERATOR_USER.format(
        parsed_resume=state["parsed_resume"],
        match_analysis=state["match_analysis"],
        pinned_context_hint=pinned_hint,
    )

    try:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(InterviewQuestions)
        result: InterviewQuestions = await structured_llm.ainvoke([
            ("system", QUESTION_GENERATOR_SYSTEM),
            ("human", user_msg),
        ])
        return {
            "interview_questions": result.model_dump(mode="json"),
            "progress": {"stage": "generate", "percentage": 85, "message": "面试题生成完成"},
            "agent_traces": [{"node": "generate_questions", "status": "ok"}],
        }
    except Exception as e:
        return {
            "errors": [f"面试出题失败：{e}"],
            "progress": {"stage": "generate", "percentage": 85, "message": "面试题生成失败"},
            "agent_traces": [{"node": "generate_questions", "status": "error", "error": str(e)}],
        }
