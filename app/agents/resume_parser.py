from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_deepseek import ChatDeepSeek

from app.agents.prompts import RESUME_PARSER_SYSTEM, RESUME_PARSER_USER
from app.agents.state import AgentState
from app.models.schemas import ResumeSchema
from config import settings

if TYPE_CHECKING:
    from app.memory.short_term import ShortTermMemory


@lru_cache(1)
def _get_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=settings.deepseek_api_key,
        api_base="https://api.deepseek.com",
        temperature=0.1,
        request_timeout=120,
        model_kwargs={
            "tool_choice": "auto",
        },
        extra_body={"thinking": {"type": "disabled"}},
    )


def _build_pinned_hint(state: AgentState) -> str:
    ctx = state.get("pinned_context") or {}
    hints = []
    if "resume" in ctx:
        hints.append("提示：用户固定了之前的简历可供参考。")
    if "job_description" in ctx:
        hints.append("提示：用户固定了职位描述作为上下文。")
    return "\n".join(hints)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_parse_resume_node(short_term: ShortTermMemory | None):
    """创建简历解析节点（带缓存）。

    如果 short_term 可用，对相同用户 + 相同简历内容会跳过 LLM。
    """

    async def node(state: AgentState) -> dict:
        if not state.get("raw_text"):
            return {
                "errors": ["简历解析失败：缺少原始文本"],
                "progress": {"stage": "parse", "percentage": 40, "message": "简历解析失败：缺少原始文本"},
            }

        user_id = state.get("user_id", "")
        text = state["raw_text"]
        text_h = _text_hash(text)

        # ── 缓存命中 ──────────────────────────────────────────
        if short_term:
            cache_key = f"resume_parse:{user_id}:{text_h}"
            cached = await short_term.cache_get(cache_key)
            if cached is not None:
                try:
                    data = json.loads(cached)
                    from app.models.schemas import ResumeSchema
                    ResumeSchema(**data)  # 校验
                    return {
                        "parsed_resume": data,
                        "progress": {"stage": "parse", "percentage": 40, "message": "简历解析完成（缓存）"},
                        "agent_traces": [{"node": "parse_resume", "status": "cache_hit"}],
                    }
                except Exception:
                    pass  # 缓存异常，重新调用 LLM

        # ── 调用 LLM ───────────────────────────────────────────
        pinned_hint = _build_pinned_hint(state)
        user_msg = RESUME_PARSER_USER.format(
            raw_text=text,
            pinned_context_hint=pinned_hint,
        )

        try:
            llm = _get_llm()
            structured_llm = llm.with_structured_output(ResumeSchema)
            result: ResumeSchema = await structured_llm.ainvoke([
                ("system", RESUME_PARSER_SYSTEM),
                ("human", user_msg),
            ])

            data = result.model_dump(mode="json")

            # 写入缓存
            if short_term:
                await short_term.cache_set(
                    cache_key,
                    json.dumps(data, ensure_ascii=False),
                    ttl=86400,  # 24 小时
                )

            return {
                "parsed_resume": data,
                "progress": {"stage": "parse", "percentage": 40, "message": "简历解析完成"},
                "agent_traces": [{"node": "parse_resume", "status": "ok"}],
            }
        except Exception as e:
            return {
                "errors": [f"简历解析失败：{e}"],
                "progress": {"stage": "parse", "percentage": 40, "message": "简历解析失败"},
                "agent_traces": [{"node": "parse_resume", "status": "error", "error": str(e)}],
            }

    return node
