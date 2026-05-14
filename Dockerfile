# ── 构建阶段：安装依赖 ─────────────────────────────────
FROM python:3.13-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app

# 先复制依赖声明文件，利用 Docker 缓存层
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ── 运行阶段 ───────────────────────────────────────────
FROM python:3.13-slim

RUN groupadd -r app && useradd -r -g app -d /app app

WORKDIR /app

# 从构建阶段复制 .venv
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码
COPY --chown=app:app . .

EXPOSE 8000

USER app

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
