from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, StateGraph

from app.agents.matching_analyst import analyze_match_node
from app.agents.question_generator import generate_questions_node
from app.agents.resume_parser import create_parse_resume_node
from app.agents.state import AgentState
from app.memory.manager import MemoryManager


def _route_after_parse(state: AgentState) -> Literal["analyze_match", "format_output"]:
    """解析完成后决定下一步：解析成功则进行匹配分析，失败则直接返回。"""
    if state.get("errors") and not state.get("parsed_resume"):
        return "format_output"
    return "analyze_match"


def _route_after_match(state: AgentState) -> Literal["generate_questions", "format_output"]:
    """匹配分析完成后决定下一步：匹配成功则出题，失败则直接返回。"""
    if state.get("errors") and not state.get("match_analysis"):
        return "format_output"
    return "generate_questions"


def _route_after_questions(state: AgentState) -> Literal["save_to_memory", "format_output"]:
    """出题完成后决定下一步：无错误则保存到记忆系统，否则直接返回。"""
    if not state.get("errors"):
        return "save_to_memory"
    return "format_output"


def build_graph(
    memory_manager: MemoryManager,
    checkpointer: RedisSaver | None = None,
) -> StateGraph:
    """构建并编译 LangGraph 状态图。

    流程：
    load_pinned_context → extract_text → parse_resume → analyze_match
    → generate_questions → save_to_memory → format_output → END

    每个关键节点后都有条件路由，出错时自动跳过下游节点。
    """

    # ── 节点：加载用户固定的上下文 ────────────────────────────────────
    async def load_pinned_context(state: AgentState) -> dict:
        """从 Redis/PG 加载用户固定的内容（简历、JD 等），注入 Agent 上下文。"""
        ctx = await memory_manager.get_pinned_context(state.get("user_id", ""))
        return {
            "pinned_context": ctx or {},
            "progress": {"stage": "load_pinned", "percentage": 10, "message": "已加载固定上下文"},
        }

    # ── 节点：文本预处理（占位） ──────────────────────────────────────
    async def extract_text(state: AgentState) -> dict:
        """文本预处理占位节点（文本已在路由层提取完毕）。"""
        return {
            "progress": {"stage": "extract", "percentage": 15, "message": "文本预处理完成"},
        }

    # ── 节点：保存结果到记忆系统 ──────────────────────────────────────
    async def save_to_memory(state: AgentState) -> dict:
        """将本次面试分析结果持久化到 Redis（短期）和 PostgreSQL（长期）。"""
        try:
            await memory_manager.save_interview_result(
                session_id=state.get("session_id", ""),
                user_id=state.get("user_id", ""),
                resume_id=None,
                job_description=state.get("job_requirements"),
                parsed_resume=state.get("parsed_resume"),
                match_report=state.get("match_analysis"),
                questions=state.get("interview_questions") or {},
            )
            return {
                "progress": {"stage": "save", "percentage": 95, "message": "分析结果已保存"},
                "agent_traces": [{"node": "save_to_memory", "status": "ok"}],
            }
        except Exception as e:
            return {
                "progress": {"stage": "save", "percentage": 95, "message": "保存结果时出错"},
                "errors": [f"记忆保存失败：{e}"],
            }

    # ── 节点：格式化输出（占位） ──────────────────────────────────────
    async def format_output(state: AgentState) -> dict:
        """输出格式化占位节点（最终响应在路由层组装）。"""
        return {
            "progress": {"stage": "done", "percentage": 100, "message": "分析流程已完成"},
        }

    # ── 构建状态图 ─────────────────────────────────────────────────
    builder = StateGraph(AgentState)

    builder.add_node("load_pinned_context", load_pinned_context)
    builder.add_node("extract_text", extract_text)
    builder.add_node("parse_resume", create_parse_resume_node(memory_manager.short_term))
    builder.add_node("analyze_match", analyze_match_node)
    builder.add_node("generate_questions", generate_questions_node)
    builder.add_node("save_to_memory", save_to_memory)
    builder.add_node("format_output", format_output)

    builder.set_entry_point("load_pinned_context")

    builder.add_edge("load_pinned_context", "extract_text")
    builder.add_edge("extract_text", "parse_resume")
    builder.add_conditional_edges("parse_resume", _route_after_parse)
    builder.add_conditional_edges("analyze_match", _route_after_match)
    builder.add_conditional_edges("generate_questions", _route_after_questions)
    builder.add_edge("save_to_memory", "format_output")
    builder.add_edge("format_output", END)

    return builder.compile(checkpointer=checkpointer)
