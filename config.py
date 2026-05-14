from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # ── DeepSeek 配置 ──
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-pro"

    # ── Redis 配置 ──
    redis_url: str = "redis://localhost:6379/0"

    # ── PostgreSQL / SQLAlchemy 配置 ──
    pg_dsn: str = "postgresql://postgres:postgres@localhost:5432/interview_assistant"
    db_pool_size: int = 5          # 连接池大小
    db_max_overflow: int = 10      # 最大溢出连接数
    db_echo: bool = False          # 是否打印 SQL 日志

    # ── 服务配置 ──
    host: str = "0.0.0.0"
    port: int = 8000

    # ── 记忆系统配置 ──
    short_term_ttl: int = 86400  # 短期记忆过期时间：24 小时
    cache_ttl: int = 3600       # 缓存过期时间：1 小时

    # ── JWT 认证配置 ──
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 小时


settings = Settings()
