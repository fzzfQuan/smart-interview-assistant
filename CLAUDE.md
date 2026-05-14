# CLAUDE.md

本文件为 Claude Code 提供本项目的代码库指引。

## 项目简介

基于 LangGraph 多 Agent 协作的智能面试提效系统。上传简历 → 自动解析 → 匹配度分析 → 面试出题。使用 Redis 实现短期记忆，PostgreSQL 实现长期用户画像存储。

## 常用命令

- **启动开发服务器**: `uv run uvicorn main:app --reload`
- **添加依赖**: `uv add <package>`
- **查看依赖树**: `uv tree`
- **代码检查**: `uv run ruff check app/ main.py config.py`

## 技术栈

- **框架**: FastAPI
- **Agent 编排**: LangGraph（StateGraph + 条件路由）
- **LLM**: langchain-deepseek（ChatDeepSeek + with_structured_output 结构化输出）
- **记忆系统**: Redis（短期：会话状态、缓存）、PostgreSQL + SQLAlchemy 2.0 async ORM（长期：用户画像、面试历史、固定记录）
- **文件解析**: PyMuPDF（PDF）、python-docx（DOCX）
- **包管理**: uv，Python 3.13

## 架构概览

### 多 Agent 流水线

每次上传简历触发完整的 LangGraph 流程：

```
load_pinned_context → extract_text → parse_resume → analyze_match → generate_questions → save_to_memory → format_output
```

每个关键节点后都有条件路由——如果解析或匹配失败，自动跳过下游节点并返回错误信息。

### 四个 Agent

| Agent | 职责 | 输出 |
|-------|------|------|
| 简历解析 (Parser) | 从原始文本提取结构化信息 | 个人信息 / 技能 / 经历 / 教育 / 项目 |
| 匹配分析 (Analyst) | 简历与职位要求对比评分 | 总体评分 / 分类得分 / 优势 / 差距 |
| 面试出题 (Generator) | 定制化生成面试题 | 技术题 / 行为题 / 项目深挖题 |
| 编排器 (Supervisor) | 图编排 + 记忆管理回调 | 协调各节点执行顺序 |

### 三层记忆系统

| 层级 | 存储 | 用途 | 过期 |
|------|------|------|------|
| 短期记忆 | Redis | 会话状态、消息历史、LLM 缓存、活跃会话 | 24 小时 |
| 长期记忆 | PostgreSQL | 用户画像、面试记录、技能记录、固定元数据 | 永久 |
| 固定 (Pin) | Redis + PG | 用户固定的关键信息（简历 / JD / 报告 / 题目） | Redis 24h + PG 永久 |

### 项目结构

```
app/
├── api/routes.py          # FastAPI 接口（上传、Pin CRUD、会话查询、画像查询）
├── agents/
│   ├── graph.py           # LangGraph 状态图构建与编译
│   ├── state.py           # AgentState 状态类型定义
│   ├── resume_parser.py   # 简历解析节点
│   ├── matching_analyst.py# 匹配分析节点
│   ├── question_generator.py # 面试出题节点
│   └── prompts.py         # LLM 提示词模板（中文）
├── memory/
│   ├── manager.py         # MemoryManager 统一接口
│   ├── short_term.py      # Redis 短期记忆
│   ├── long_term.py       # PostgreSQL 长期记忆
│   └── pin_store.py       # Pin 机制（Redis 热读 + PG 持久）
├── models/schemas.py      # Pydantic 数据模型（中文注释）
└── services/file_parser.py # PDF/DOCX/TXT 文本提取
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/upload` | 上传简历（multipart），运行全部分析流程 |
| POST | `/api/v1/pin` | 固定一条记录 |
| DELETE | `/api/v1/pin/{pin_id}` | 取消固定 |
| GET | `/api/v1/pins` | 获取固定列表 |
| GET | `/api/v1/sessions/{session_id}` | 从 Redis 恢复会话 |
| GET | `/api/v1/users/{user_id}/profile` | 从 PostgreSQL 获取用户画像 |
| GET | `/health` | 健康检查 |

## 环境配置

复制 `.env.example` 到 `.env` 后配置：

- `DEEPSEEK_API_KEY` — DeepSeek API 密钥（必填）
- `REDIS_URL` — Redis 连接地址，默认 `redis://localhost:6379/0`
- `PG_DSN` — PostgreSQL 连接串，默认 `postgresql://postgres:postgres@localhost:5432/interview_assistant`
