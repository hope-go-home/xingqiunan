# 数据库模块：创建异步 PostgreSQL 连接，提供 ORM 基类和会话管理

from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import DATABASE_URL

# 异步引擎：连接池默认创建，echo=False 不打印 SQL 日志
engine = create_async_engine(DATABASE_URL, echo=False)

# 会话工厂：每次请求通过 get_db() 获取一个独立会话
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 基类，所有模型继承此类，init_db() 时自动建表"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入函数，路由里声明 db: AsyncSession = Depends(get_db) 即可使用"""
    async with async_session() as session:
        yield session


async def init_db():
    """应用启动时调用：用 Alembic 子进程管理表结构。

    用子进程而非 in-process 的 command.upgrade：在 Windows + Python 3.13 下，
    进程内跑 Alembic 会卡死在 startup 阶段（实测命令行秒过、进程内必卡）。
    子进程是干净环境，且不影响父进程的日志配置。
    """
    import asyncio
    import subprocess
    import sys

    backend_dir = str(Path(__file__).resolve().parents[2])

    def _run() -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

    result = await asyncio.to_thread(_run)
    if result.returncode != 0:
        raise RuntimeError(f"Alembic 迁移失败:\n{result.stdout}\n{result.stderr}")
