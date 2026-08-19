# FastAPI 应用入口：组装路由、中间件、启动事件

import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ALLOWED_ORIGINS, LOG_DIR
from app.core.database import init_db
from app.models.chat_message import ChatMessage  # 确保 chat_history 表创建
from app.models.token_usage import TokenUsage  # 确保 token_usage 表创建
from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.tasks import router as tasks_router
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router

# 日志配置：stdout + 滚动文件（logs/app.log，单文件 5MB 保留 3 份），时间戳 + 级别 + 模块
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
)
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    _file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    _file_handler.setFormatter(logging.Formatter(LOG_FORMAT, "%Y-%m-%d %H:%M:%S"))
    logging.getLogger().addHandler(_file_handler)
except Exception as e:
    logging.getLogger(__name__).warning("文件日志初始化失败，仅保留 stdout: %s", e)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动建表"""
    await init_db()
    logger.info("TaskBench 后端启动完成")
    yield


app = FastAPI(title="智能任务自动化工作台", lifespan=lifespan)

# 跨域配置：仅允许白名单来源（.env ALLOWED_ORIGINS 配置）
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
