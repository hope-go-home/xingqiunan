import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# 确保项目根目录在 sys.path 中（alembic/ 子目录运行时需要找到 app 包）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import DATABASE_URL
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.file_record import FileRecord
from app.models.task import Task
from app.models.token_usage import TokenUsage
from app.core.database import Base

# Alembic Config object
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置目标 metadata（autogenerate 依赖）
target_metadata = Base.metadata


def _sync_url() -> str:
    """把 asyncpg URL 转为 psycopg2 URL（Alembic 需要同步驱动）"""
    url = DATABASE_URL
    # postgresql+asyncpg:// → postgresql://
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    # 如果已经是同步的就直接返回
    return url


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL 脚本，不连数据库"""
    url = _sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接连数据库执行迁移"""
    url = _sync_url()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
