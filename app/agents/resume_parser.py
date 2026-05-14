from __future__ import annotations

from functools import lru_cache

from langchain_deepseek import ChatDeepSeek

from app.agents.prompts import RESUME_PARSER_SYSTEM, RESUME_PARSER_USER
from app.agents.state import AgentState
from app.models.schemas import ResumeSchema
from config import settings


@lru_cache(1)
def _get_llm() -> ChatDeepSeek:
    """懒加载 LLM 实例（带缓存），避免无 API Key 时导入报错。"""

    return ChatDeepSeek(
        model="deepseek-v4-flash",
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
    if "resume" in ctx:
        hints.append("提示：用户固定了之前的简历可供参考。")
    if "job_description" in ctx:
        hints.append("提示：用户固定了职位描述作为上下文。")
    return "\n".join(hints)


async def parse_resume_node(state: AgentState) -> dict:
    """简历解析节点：从原始文本中提取结构化简历数据。"""

    if not state.get("raw_text"):
        return {
            "errors": ["简历解析失败：缺少原始文本"],
            "progress": {"stage": "parse", "percentage": 40, "message": "简历解析失败：缺少原始文本"},
        }

    pinned_hint = _build_pinned_hint(state)
    user_msg = RESUME_PARSER_USER.format(
        raw_text=state["raw_text"],
        pinned_context_hint=pinned_hint,
    )

    try:
        llm = _get_llm()
        structured_llm = llm.with_structured_output(ResumeSchema)
        result: ResumeSchema = await structured_llm.ainvoke([
            ("system", RESUME_PARSER_SYSTEM),
            ("human", user_msg),
        ])

        print('result', result)
        return {
            "parsed_resume": result.model_dump(mode="json"),
            "progress": {"stage": "parse", "percentage": 40, "message": "简历解析完成"},
            "agent_traces": [{"node": "parse_resume", "status": "ok"}],
        }
    except Exception as e:
        print(e, 'e')
        return {
            "errors": [f"简历解析失败：{e}"],
            "progress": {"stage": "parse", "percentage": 40, "message": "简历解析失败"},
            "agent_traces": [{"node": "parse_resume", "status": "error", "error": str(e)}],
        }
