from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.routes import create_router
from app.memory.manager import MemoryManager

memory_manager = MemoryManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期：启动时初始化数据库连接，关闭时清理资源。"""
    # ── 启动：初始化数据库连接池、创建表结构 ──
    await memory_manager.initialize()
    app.state.memory_manager = memory_manager
    yield
    # ── 关闭：释放 Redis 和 PostgreSQL 连接 ──
    await memory_manager.close()


app = FastAPI(
    title="智能面试助手",
    description="基于 LangGraph 多 Agent 协作的智能面试提效系统，支持简历解析、匹配度分析、面试出题",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(create_router(memory_manager), prefix="/api/v1")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def index():
    """返回前台页面。"""
    return FileResponse("app/static/index.html")


@app.get("/health")
async def health():
    """健康检查接口。"""
    return {"status": "ok"}
