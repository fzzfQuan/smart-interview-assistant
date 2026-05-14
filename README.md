智能面试提效系统 — 架构规划                                                                                                                               
                                                                                                                                                      
 Context

 构建一个基于 LangGraph 多 Agent
 协作的智能面试辅助系统。用户上传简历，系统自动解析、分析匹配度、生成面试题，帮助面试官高效准备面试。当前项目仅有脚手架代码，需从零设计整体架构。

 新增需求：引入记忆系统，包括 Pin 机制固定关键信息、Redis 加速短期记忆、PostgreSQL 存储长期记忆（用户面试画像、多轮面试数据）。

 ---
 一、系统流程

 用户上传简历(PDF)
     → 文件解析 (提取文本)
     → 简历解析 (Resume Parser Agent)
     → 简历匹配度分析 (Matching Analyst Agent)
     → 面试出题 (Interview Generator Agent)
     → 结果持久化 → 返回

 二、技术选型

 ┌────────────────────────┬───────────────────────────────┬───────────────────────────────────┐
 │          层面          │             选择              │               理由                │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ Web 框架               │ FastAPI                       │ 已引入，异步支持好                │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ Agent 编排             │ LangGraph                     │ 已引入，状态图驱动多 Agent        │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ LLM                    │ DeepSeek (langchain-deepseek) │ 已引入                            │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ 文件处理               │ PyMuPDF / python-docx         │ PDF/DOCX 解析                     │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ 结构化输出             │ Pydantic                      │ LangChain 原生集成                │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ 短期记忆               │ Redis (redis-py)              │ 低延迟，session 级缓存 + 消息历史 │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ 长期记忆               │ PostgreSQL (asyncpg)          │ 持久化用户画像、多轮面试数据      │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ LangGraph Checkpointer │ RedisSaver + PostgresSaver    │ 状态断点续传 + 会话恢复           │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ 包管理                 │ uv                            │ 已用                              │
 ├────────────────────────┼───────────────────────────────┼───────────────────────────────────┤
 │ 环境变量               │ python-dotenv                 │ 已引入                            │
 └────────────────────────┴───────────────────────────────┴───────────────────────────────────┘

 ---
 三、记忆系统架构

                     ┌──────────────────────────────────┐
                     │         MemoryManager              │
                     │   (统一读写接口，Agent 无感调用)     │
                     └──────┬────────────┬───────────────┘
                            │            │
               ┌────────────┘            └────────────┐
               ▼                                       ▼
     ┌──────────────────┐                  ┌────────────────────┐
     │   Short-Term     │                  │   Long-Term        │
     │   (Redis)        │                  │   (PostgreSQL)     │
     │                  │                  │                    │
     │  • Session State │                  │  • 用户面试画像      │
     │  • Agent 消息历史 │                  │  • 多轮面试记录      │
     │  • 当前解析缓存   │                  │  • Pin 元数据       │
     │  • Pin 热数据     │                  │  • 历史匹配分析报告  │
     │  • TTL: 24h      │                  │  • 统计聚合数据      │
     └──────────────────┘                  └────────────────────┘

            ▼                                       ▼
     ┌──────────────────────────────────────────────────────┐
     │              LangGraph Checkpointer                   │
     │  • RedisSaver: 会话级状态快照 (short-term)            │
     │  • PostgresSaver: 跨会话状态持久化 (long-term)       │
     └──────────────────────────────────────────────────────┘

 3.1 Pin 机制

 Pin 是用户显式"固定"的关键信息，同时写 Redis（热）和 PostgreSQL（持久）。

 ┌───────────────────────────────────────┬───────────────────────────────────┬─────────────────────────┐
 │                 操作                  │               说明                │          存储           │
 ├───────────────────────────────────────┼───────────────────────────────────┼─────────────────────────┤
 │ pin(user_id, type, item_id, metadata) │ 固定某条数据                      │ Redis Hash + PG pins 表 │
 ├───────────────────────────────────────┼───────────────────────────────────┼─────────────────────────┤
 │ unpin(user_id, pin_id)                │ 取消固定                          │ 两者同步删除            │
 ├───────────────────────────────────────┼───────────────────────────────────┼─────────────────────────┤
 │ list_pins(user_id, type_filter)       │ 列出固定项                        │ 优先 Redis，回源 PG     │
 ├───────────────────────────────────────┼───────────────────────────────────┼─────────────────────────┤
 │ get_pinned_context(user_id)           │ 获取所有固定内容用于 Agent 上下文 │ 合并所有 Pin 类型       │
 └───────────────────────────────────────┴───────────────────────────────────┴─────────────────────────┘

 Pin 类型枚举：
 - resume — 简历
 - job_description — 职位描述
 - analysis_report — 分析报告
 - interview_questions — 面试题
 - custom_note — 自定义备注

 3.2 短期记忆 (Redis)

 ┌────────────────────────────┬─────────────────────────────┬───────────────────┐
 │          Key 模式          │            用途             │        TTL        │
 ├────────────────────────────┼─────────────────────────────┼───────────────────┤
 │ session:{sid}:state        │ LangGraph 状态快照          │ 24h               │
 ├────────────────────────────┼─────────────────────────────┼───────────────────┤
 │ session:{sid}:messages     │ Agent 对话历史 (最近 N 轮)  │ 24h               │
 ├────────────────────────────┼─────────────────────────────┼───────────────────┤
 │ session:{sid}:cache:{key}  │ LLM 调用结果缓存            │ 1h                │
 ├────────────────────────────┼─────────────────────────────┼───────────────────┤
 │ user:{uid}:pins            │ Pin 热数据 (加速 list_pins) │ 跟随 Pin 生命周期 │
 ├────────────────────────────┼─────────────────────────────┼───────────────────┤
 │ user:{uid}:active_sessions │ 用户活跃会话列表            │ 24h               │
 └────────────────────────────┴─────────────────────────────┴───────────────────┘

 3.3 长期记忆 (PostgreSQL)

 核心表设计：

 -- 用户面试画像
 CREATE TABLE user_profiles (
     user_id UUID PRIMARY KEY,
     aggregated_skills JSONB,       -- 聚合技能图谱
     experience_summary TEXT,        -- 经验摘要
     interview_count INT DEFAULT 0,
     avg_match_score FLOAT,
     updated_at TIMESTAMPTZ
 );

 -- 多轮面试记录
 CREATE TABLE interview_sessions (
     session_id UUID PRIMARY KEY,
     user_id UUID REFERENCES user_profiles,
     resume_id UUID,
     job_description TEXT,
     match_report JSONB,            -- 匹配分析完整结果
     questions JSONB,               -- 生成的面试题
     feedback JSONB,                -- 面试反馈/评分
     created_at TIMESTAMPTZ
 );

 -- Pin 元数据
 CREATE TABLE pins (
     pin_id UUID PRIMARY KEY,
     user_id UUID NOT NULL,
     pin_type VARCHAR(50) NOT NULL, -- resume/jd/analysis/questions/note
     item_id UUID NOT NULL,
     metadata JSONB,               -- 标签、备注、自定义字段
     pinned_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE(user_id, pin_type, item_id)
 );

 -- 技能标签索引 (用于画像聚合)
 CREATE TABLE skill_records (
     user_id UUID REFERENCES user_profiles,
     skill_name VARCHAR(200),
     category VARCHAR(50),          -- language/framework/tool/soft
     proficiency FLOAT,             -- 熟练度 0-1
     encounter_count INT DEFAULT 1,
     last_seen_at TIMESTAMPTZ
 );

 3.4 LangGraph Checkpointer 集成

 # 双 Checkpointer 策略
 short_term_checkpointer = RedisSaver(redis_client)   # session 粒度的状态恢复
 long_term_checkpointer = PostgresSaver(pg_pool)      # 跨 session 的用户画像更新

 graph = StateGraph(AgentState)
 # 运行时传入 short_term_checkpointer，节点内部回调 long_term 做持久化

 Supervisor Agent 在每个节点执行完毕后：
 1. 自动由 RedisSaver 保存状态快照 (LangGraph 原生)
 2. 主动调用 MemoryManager 更新长期记忆 (用户画像聚合、面试记录)

 ---
 四、多 Agent 架构 (LangGraph)

 State Graph

 class AgentState(TypedDict):
     raw_text: str                    # 简历原始文本
     parsed_resume: ResumeSchema      # 结构化简历
     job_requirements: str | None     # 职位要求
     match_analysis: MatchReport      # 匹配分析
     interview_questions: InterviewQuestions  # 面试题
     session_id: str                  # LangGraph checkpointer session
     user_id: str
     pinned_context: dict             # 从 Pin 加载的上下文
     errors: list[str]

                     ┌─────────────────────────┐
                     │   SupervisorAgent         │
                     │   流程编排 + Memory 管理   │
                     └────────┬────────────────┘
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │  Resume    │ │  Matching │ │ Interview  │
       │  Parser   │ │  Analyst  │ │ Generator  │
       └────────────┘ └────────────┘ └────────────┘
               │              │              │
               ▼              ▼              ▼
       ┌──────────────────────────────────────────┐
       │   MemoryManager (每个节点结束后回调)       │
       │   • 写 Redis 短期状态                      │
       │   • 更新 PostgreSQL 用户画像               │
       │   • 同步 Pin 状态                          │
       └──────────────────────────────────────────┘

 Agent 职责

 1. Resume Parser Agent

 - 输入: 简历原始文本
 - 输出: 结构化简历 (Pydantic Schema)
 - 功能: 提取个人信息、技能、经历、教育、项目；技能标准化归类

 2. Matching Analyst Agent

 - 输入: ResumeSchema + 职位要求 (可选)
 - 输出: MatchReport (匹配评分 + 差距分析 + 优劣势)
 - 功能: 技能匹配度计算、经验对标、Gap 识别

 3. Interview Generator Agent

 - 输入: ResumeSchema + MatchReport
 - 输出: 分层面试题 (技术/行为/项目深挖)
 - 功能: 按难度分级出题，基于简历深度定制

 4. Supervisor Agent

 - 定义 StateGraph 节点路由
 - 维护 AgentState
 - 调用 MemoryManager 做记忆读写
 - 错误处理和重试

 LangGraph 节点编排

 nodes:
   load_pinned_context   # 从 Redis/PG 加载用户 Pin 数据 → state.pinned_context
   extract_text          # 解析 PDF/DOCX → raw_text
   parse_resume          # Resume Parser Agent (LLM 调用)
   analyze_match         # Matching Analyst Agent (LLM 调用)
   generate_questions    # Interview Generator Agent (LLM 调用)
   save_to_memory        # 写 Redis 短期 + PG 长期 + Pin
   format_output         # 组装最终响应

 edges:
   START → load_pinned_context
   load_pinned_context → extract_text
   extract_text → parse_resume
   parse_resume → analyze_match
   analyze_match → generate_questions
   generate_questions → save_to_memory
   save_to_memory → format_output
   format_output → END

 # Checkpointer: RedisSaver (session 恢复)
 # 每个 LLM 节点执行后自动保存 checkpoint

 ---
 五、项目目录结构

 smart-interview-assistant/
 ├── main.py                       # FastAPI 入口
 ├── config.py                     # Redis/PG 连接配置
 ├── pyproject.toml
 ├── .env                          # API Keys + DB 连接串 (gitignored)
 ├── app/
 │   ├── __init__.py
 │   ├── api/
 │   │   ├── __init__.py
 │   │   ├── routes.py             # FastAPI 路由
 │   │   └── schemas.py            # API 请求/响应模型
 │   ├── agents/
 │   │   ├── __init__.py
 │   │   ├── state.py              # AgentState TypedDict
 │   │   ├── graph.py              # LangGraph StateGraph
 │   │   ├── resume_parser.py      # Resume Parser Agent
 │   │   ├── matching_analyst.py   # Matching Analyst Agent
 │   │   ├── question_generator.py # Interview Generator Agent
 │   │   └── prompts.py            # 提示词模板
 │   ├── memory/
 │   │   ├── __init__.py
 │   │   ├── manager.py            # MemoryManager 统一接口
 │   │   ├── short_term.py         # Redis 短期记忆实现
 │   │   ├── long_term.py          # PostgreSQL 长期记忆实现
 │   │   ├── pin_store.py          # Pin 机制 (Redis + PG)
 │   │   └── models.py             # 记忆相关 Pydantic Schema
 │   ├── models/
 │   │   ├── __init__.py
 │   │   └── schemas.py            # ResumeSchema, MatchReport, Question
 │   └── services/
 │       ├── __init__.py
 │       └── file_parser.py        # PDF/DOCX 文件解析
 └── tests/
     ├── __init__.py
     ├── test_agents.py
     └── test_memory.py

 ---
 六、API 设计

 POST /upload          # 上传简历，自动全流程分析
       Request:  multipart/form-data (file + optional job_description)
       Response: { session_id, parsed_resume, match_analysis, interview_questions }

 POST /pin             # 固定某条记录
       Request:  { user_id, pin_type, item_id, metadata? }

 DELETE /pin/{pin_id}  # 取消固定

 GET /pins             # 获取固定列表
       Query: user_id, type_filter?

 GET /sessions/{session_id}  # 恢复历史 session (从 Redis Checkpointer)
 GET /users/{user_id}/profile  # 获取用户面试画像 (从 PG)

     GET /users/{user_id}/profile  # 获取用户面试画像 (从 PG)

     ---
     七、验证方式

     1. 安装依赖: uv add redis asyncpg pymupdf python-docx
     2. 本地启动 Redis + PostgreSQL (docker compose)
     3. uv run uvicorn main:app --reload 启动服务
     4. POST /upload 上传测试简历 → 检查结构化输出
     5. POST /pin 固定结果 → GET /pins 确认持久化
     6. 重新请求 GET /sessions/{session_id} → 确认状态恢复
     7. 检查 PG interview_sessions 表记录完整性

     ---
     八、后续可扩展方向

     - RAG 面试题 — 基于 Pin 的 JD + 简历做检索增强出题
     - 面试模拟 Agent — LLM 扮演面试官，基于出题列表对话
     - 反馈闭环 — 面试后评分写入 PG，迭代优化匹配模型
     - 技能图谱 — 跨用户聚合 skill_records，构建行业技能热力图
