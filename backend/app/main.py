# FastAPI 应用入口：组装路由、中间件、启动事件

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.models.chat_message import ChatMessage  # 确保 chat_history 表创建
from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.tasks import router as tasks_router
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动建表"""
    await init_db()
    yield


app = FastAPI(title="智能任务自动化工作台", lifespan=lifespan)

# 跨域配置：开发阶段允许本地前端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)       # /auth/register, /auth/login
app.include_router(files_router)      # /files/upload
app.include_router(tasks_router)      # /tasks/
app.include_router(chat_router)       # /chat/ws  WebSocket
app.include_router(knowledge_router)  # /knowledge/add, /search, /list, /delete
