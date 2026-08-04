# 数据库模块：创建异步 PostgreSQL 连接，提供 ORM 基类和会话管理

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
    """应用启动时调用，自动创建所有继承 Base 的表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
