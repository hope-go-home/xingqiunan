# Celery 异步任务配置：用于后台处理耗时任务（如大文件解析、批量转换）
# 需启动 Celery Worker 才能执行任务

from celery import Celery
from app.core.config import REDIS_URL

# 使用 Redis 作为任务队列
celery_app = Celery(
    "smart_agent",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)
