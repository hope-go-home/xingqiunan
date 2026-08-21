# FastAPI 应用入口：组装路由、中间件、启动事件、可观测性

import logging
import os
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.core.config import ALLOWED_ORIGINS, LOG_DIR
from app.core.database import init_db
from app.models.chat_message import ChatMessage  # 确保 chat_history 表创建
from app.models.token_usage import TokenUsage  # 确保 token_usage 表创建
from app.models.user_preference import UserPreference  # 确保 user_preferences 表创建
from app.api.auth import router as auth_router
from app.api.files import router as files_router
from app.api.tasks import router as tasks_router
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router
from app.core.metrics import http_requests_total, http_request_duration_seconds

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


# ─── Prometheus 指标中间件：自动记录每个请求的计数+耗时 ───

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    return response


# ─── /healthz 健康检查：负载均衡器/监控平台定期探测 ───

@app.get("/healthz", tags=["系统"])
async def healthz():
    """健康检查：检查数据库和 Redis 连通性"""
    checks = {"status": "ok", "checks": {}}

    # 数据库
    try:
        from app.core.database import async_session
        from sqlalchemy import text as sql_text
        async with async_session() as db:
            await db.execute(sql_text("SELECT 1"))
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["checks"]["database"] = f"error: {e}"
        checks["status"] = "degraded"

    # Redis
    try:
        from app.api.chat import r
        redis = await r()
        await redis.ping()
        checks["checks"]["redis"] = "ok"
    except Exception as e:
        checks["checks"]["redis"] = f"error: {e}"
        checks["status"] = "degraded"

    from fastapi.responses import JSONResponse
    status_code = 200 if checks["status"] == "ok" else 503
    return JSONResponse(content=checks, status_code=status_code)


# ─── /metrics Prometheus 端点：Prometheus 抓取入口 ───

@app.get("/metrics", tags=["系统"])
async def metrics():
    """Prometheus 指标端点"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# 注册路由
app.include_router(auth_router)       # /auth/register, /auth/login
app.include_router(files_router)      # /files/upload
app.include_router(tasks_router)      # /tasks/
app.include_router(chat_router)       # /chat/ws  WebSocket
app.include_router(knowledge_router)  # /knowledge/add, /search, /list, /delete
