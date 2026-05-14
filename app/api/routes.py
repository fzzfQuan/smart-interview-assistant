from __future__ import annotations

import json
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.graph import build_graph
from app.agents.state import AgentState
from app.api.deps import get_current_user
from app.memory.manager import MemoryManager
from app.models.db_models import User
from app.models.schemas import (
    InterviewQuestions,
    MatchReport,
    PinListResponse,
    PinRequest,
    PinResponse,
    ResumeSchema,
    SessionResponse,
    UploadResponse,
    UserProfileResponse,
)
from app.services.file_parser import extract_text_from_file


def _sse(event: str, data: dict) -> str:
    """格式化 SSE 事件消息。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _init_routes(router: APIRouter, memory_manager: MemoryManager) -> None:
    """绑定路由处理器，注入 memory_manager 实例。"""

    @router.post("/upload", response_model=UploadResponse)
    async def upload_resume(
        file: UploadFile = File(...),
        job_description: str | None = Form(None),
        user_id: str = Form("default-user"),
        current_user: User | None = Depends(get_current_user),
    ):
        """上传简历（PDF/DOCX/TXT），自动执行全部分析流程并返回结果。"""
        # 如果已登录，使用认证用户的 ID
        effective_user_id = str(current_user.id) if current_user else user_id
        allowed = {".pdf", ".docx", ".txt"}
        ext = Path(file.filename or "").suffix.lower()
        if ext not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式 '{ext}'，仅支持：{', '.join(allowed)}",
            )

        # 将上传的文件保存到临时位置
        content = await file.read()
        with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 从文件中提取纯文本
            raw_text = await extract_text_from_file(tmp_path)
            if not raw_text:
                raise HTTPException(
                    status_code=400,
                    detail="无法从上传的文件中提取文本，请确认文件包含可选中的文字内容。",
                )

            # 初始化状态并运行 LangGraph 流水线
            session_id = str(uuid.uuid4())
            state: AgentState = {
                "raw_text": raw_text,
                "parsed_resume": None,
                "job_requirements": job_description,
                "match_analysis": None,
                "interview_questions": None,
                "session_id": session_id,
                "user_id": effective_user_id,
                "pinned_context": None,
                "errors": [],
                "agent_traces": [],
            }

            graph = build_graph(memory_manager)
            result = await graph.ainvoke(state)

            if result.get("errors"):
                raise HTTPException(
                    status_code=500,
                    detail=result["errors"],
                )

            return UploadResponse(
                session_id=session_id,
                parsed_resume=ResumeSchema(**result["parsed_resume"]),
                match_analysis=MatchReport(**result["match_analysis"]),
                interview_questions=InterviewQuestions(**result["interview_questions"]),
            )

        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    @router.post("/upload/stream")
    async def upload_resume_stream(
        file: UploadFile = File(...),
        job_description: str | None = Form(None),
        user_id: str = Form("default-user"),
        current_user: User | None = Depends(get_current_user),
    ):
        """上传简历（流式），SSE 格式实时推送进度和最终结果。"""
        effective_user_id = str(current_user.id) if current_user else user_id
        allowed = {".pdf", ".docx", ".txt"}
        ext = Path(file.filename or "").suffix.lower()
        if ext not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式 '{ext}'，仅支持：{', '.join(allowed)}",
            )

        content = await file.read()
        with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        async def event_stream():
            try:
                raw_text = await extract_text_from_file(tmp_path)
                if not raw_text:
                    yield _sse("error", {"message": "无法从文件中提取文本，请确认文件包含可选中的文字内容。"})
                    return

                session_id = str(uuid.uuid4())
                initial_state: AgentState = {
                    "raw_text": raw_text,
                    "parsed_resume": None,
                    "job_requirements": job_description,
                    "match_analysis": None,
                    "interview_questions": None,
                    "session_id": session_id,
                    "user_id": effective_user_id,
                    "pinned_context": None,
                    "errors": [],
                    "progress": None,
                    "agent_traces": [],
                }

                graph = build_graph(memory_manager)

                yield _sse("meta", {"session_id": session_id})
                yield _sse("progress", {"stage": "start", "percentage": 0, "message": "正在启动分析流程..."})

                last_state: AgentState | None = None
                try:
                    async for _node_name, state in graph.astream(initial_state):
                        last_state = state
                        progress = state.get("progress")
                        if progress:
                            yield _sse("progress", progress)
                except Exception as e:
                    yield _sse("error", {"message": f"分析流程异常：{e}"})
                    return

                if last_state and last_state.get("errors"):
                    yield _sse("error", {"message": last_state["errors"][0]})
                    return

                yield _sse("result", {
                    "session_id": session_id,
                    "parsed_resume": last_state.get("parsed_resume"),
                    "match_analysis": last_state.get("match_analysis"),
                    "interview_questions": last_state.get("interview_questions"),
                })
            except Exception as e:
                yield _sse("error", {"message": str(e)})
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ─── Pin（固定记录） ─────────────────────────────────────────────

    @router.post("/pin", response_model=PinResponse)
    async def pin_item(req: PinRequest):
        """固定一条记录（简历 / JD / 分析报告 / 面试题 等）。"""
        item = await memory_manager.pin_item(
            user_id=req.user_id,
            pin_type=req.pin_type.value,
            item_id=req.item_id,
            metadata=req.metadata,
        )
        return PinResponse(pin=item)

    @router.delete("/pin/{pin_id}")
    async def unpin_item(user_id: str = "default-user", pin_id: str = ...):
        """取消固定某条记录。"""
        success = await memory_manager.unpin_item(user_id, pin_id)
        if not success:
            raise HTTPException(status_code=404, detail="未找到该固定记录")
        return {"ok": True}

    @router.get("/pins", response_model=PinListResponse)
    async def list_pins(user_id: str = "default-user", pin_type: str | None = None):
        """获取用户的固定记录列表，可按类型筛选。"""
        items = await memory_manager.list_pins(user_id, pin_type)
        return PinListResponse(pins=items)

    # ─── 会话 ────────────────────────────────────────────────────────

    @router.get("/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str):
        """从 Redis 恢复会话状态。"""
        state = await memory_manager.get_session_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="未找到该会话")
        return SessionResponse(session_id=session_id, state=state)

    # ─── 用户画像 ────────────────────────────────────────────────────

    @router.get("/users/{user_id}/profile", response_model=UserProfileResponse)
    async def get_user_profile(user_id: str):
        """从 PostgreSQL 获取用户面试画像。"""
        profile = await memory_manager.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="未找到该用户")
        return UserProfileResponse(
            profile=profile  # type: ignore
        )


def create_router(memory_manager: MemoryManager) -> APIRouter:
    """工厂方法：创建并返回一个配置好的路由实例。"""
    r = APIRouter()
    _init_routes(r, memory_manager)
    return r
