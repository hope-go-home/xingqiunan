"""
异步任务定义：后台执行自动化任务，避免阻塞 API 响应。
启动方式：celery -A app.tasks.celery_app worker --pool=solo -l info
"""
import time
from app.tasks.celery_app import celery_app
from app.core.config import DATABASE_URL
from sqlalchemy import create_engine, text


def _update_task_status(task_id: int, status: str):
    """通过同步引擎更新任务状态"""
    try:
        sync_url = DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE tasks SET status = :status, updated_at = NOW() WHERE id = :id"),
                {"status": status, "id": task_id},
            )
            conn.commit()
        engine.dispose()
    except Exception:
        pass  # 状态更新失败不影响主任务


@celery_app.task(bind=True)
def execute_task(self, task_id: int, title: str, task_type: str, description: str = ""):
    """
    后台执行自动化任务。
    - document_process: 模拟文档解析处理
    - data_calc: 模拟数据计算
    - file_convert: 模拟文件格式转换
    """
    # 1. 更新状态为 running
    _update_task_status(task_id, "running")

    try:
        # 2. 模拟处理过程
        step_messages = {
            "document_process": [
                "正在加载文档…",
                "正在提取文本内容…",
                "正在结构化解析…",
                "文档处理完成",
            ],
            "data_calc": [
                "正在读取数据源…",
                "正在执行计算任务…",
                "正在生成计算结果…",
                "数据计算完成",
            ],
            "file_convert": [
                "正在读取源文件…",
                "正在转换格式…",
                "正在写入目标文件…",
                "文件转换完成",
            ],
        }

        steps = step_messages.get(task_type, ["正在处理…", "处理完成"])
        for i, msg in enumerate(steps):
            self.update_state(state="PROGRESS", meta={
                "task_id": task_id,
                "step": i + 1,
                "total": len(steps),
                "message": msg,
            })
            time.sleep(1.5)  # 模拟耗时操作

        # 3. 更新为 completed
        _update_task_status(task_id, "completed")
        return {"status": "completed", "task_id": task_id, "task_type": task_type}

    except Exception as e:
        _update_task_status(task_id, "failed")
        return {"status": "failed", "task_id": task_id, "error": str(e)}
